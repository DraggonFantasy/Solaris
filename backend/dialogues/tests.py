import hashlib
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .gemini_illustrations import (
    DownloadedImage,
    GeminiImageAsset,
    GeminiIllustrationImportResult,
    HttpResponse,
    canonical_gemini_share_url,
    download_gemini_image,
    extract_gemini_image_assets,
    import_gemini_illustrations,
    is_gemini_share_url,
)
from .models import AuditLog, Dialogue, DialogueIllustration, DialogueInlineImage, Section


class DialogueListViewTests(APITestCase):
    def test_section_filter_returns_only_published_dialogues_for_staff(self):
        staff = get_user_model().objects.create_user(
            username='moderator',
            password='password',
            is_staff=True,
        )
        section = Section.objects.create(
            name='Світогляд',
            slug='worldview',
            order=10,
        )
        other_section = Section.objects.create(
            name='Навчання',
            slug='learning',
            order=20,
        )
        published = Dialogue.objects.create(
            title='Published dialogue',
            section=section,
            text='Text',
            status=Dialogue.STATUS_PUBLISHED,
        )
        Dialogue.objects.create(
            title='Rejected dialogue',
            section=section,
            text='Text',
            status=Dialogue.STATUS_REJECTED,
        )
        Dialogue.objects.create(
            title='Archived dialogue',
            section=section,
            text='Text',
            status=Dialogue.STATUS_ARCHIVED,
        )
        Dialogue.objects.create(
            title='Other section dialogue',
            section=other_section,
            text='Text',
            status=Dialogue.STATUS_PUBLISHED,
        )

        self.client.force_authenticate(user=staff)
        response = self.client.get('/api/dialogues/', {'section': section.slug})

        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual([item['id'] for item in results], [published.id])


@override_settings(MEDIA_ROOT='/tmp/solaris-test-media')
class DialogueInlineImageTests(APITestCase):
    image_bytes = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
        b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username='author',
            password='password',
        )
        self.other_user = get_user_model().objects.create_user(
            username='other',
            password='password',
        )
        self.section = Section.objects.create(name='Section', slug='section')
        self.dialogue = Dialogue.objects.create(
            title='Draft dialogue',
            section=self.section,
            text='Text',
            human_author=self.author,
            status=Dialogue.STATUS_DRAFT,
        )

    def image(self):
        return SimpleUploadedFile('inline.gif', self.image_bytes, content_type='image/gif')

    def test_author_can_upload_inline_image_to_editable_dialogue(self):
        self.client.force_authenticate(user=self.author)

        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/inline-images/',
            {'image': self.image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(DialogueInlineImage.objects.filter(dialogue=self.dialogue).count(), 1)
        self.assertIn('/media/dialogue_inline_images/', response.data['image'])

    def test_other_user_cannot_upload_inline_image(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/inline-images/',
            {'image': self.image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(DialogueInlineImage.objects.exists())


class GeminiIllustrationExtractionTests(SimpleTestCase):
    def asset_record(
        self,
        filename,
        url,
        *,
        kind,
        content_type,
        width,
        height,
    ):
        return [
            None,
            1,
            filename,
            url,
            None,
            "asset-token",
            None,
            None,
            kind,
            [1_700_000_000, 0],
            None,
            content_type,
            None,
            None,
            None,
            [width, height, 1000],
        ]

    def test_extracts_uploaded_image_and_largest_generated_variant(self):
        uploaded = self.asset_record(
            "prompt.jpg",
            "https://lh3.googleusercontent.com/uploaded",
            kind=1,
            content_type="image/jpeg",
            width=1000,
            height=600,
        )
        generated_small = self.asset_record(
            "generated-small.png",
            "https://lh3.googleusercontent.com/generated-small=mp2",
            kind=2,
            content_type="image/png",
            width=1364,
            height=768,
        )
        generated_large = self.asset_record(
            "generated-large.png",
            "https://lh3.googleusercontent.com/generated-large=mp2",
            kind=2,
            content_type="image/png",
            width=2728,
            height=1536,
        )
        generated_jpeg = self.asset_record(
            "generated.jpeg",
            "https://lh3.googleusercontent.com/generated-jpeg=mp2",
            kind=2,
            content_type="image/jpeg",
            width=1364,
            height=768,
        )
        payload = [[
            None,
            [[
                None,
                None,
                [["Create a visual explanation", [[uploaded]]]],
                [[[generated_small, generated_large, generated_jpeg]]],
            ]],
        ]]

        assets = extract_gemini_image_assets(payload)

        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0].kind, "uploaded")
        self.assertEqual(assets[0].url, uploaded[3])
        self.assertEqual(assets[1].kind, "generated")
        self.assertEqual(assets[1].url, generated_large[3])
        self.assertIn("Create a visual explanation", assets[1].caption)

    def test_ignores_images_from_untrusted_hosts(self):
        external = self.asset_record(
            "external.png",
            "https://example.com/image.png",
            kind=1,
            content_type="image/png",
            width=100,
            height=100,
        )
        payload = [[None, [[None, None, [["Prompt", [external]]], []]]]]

        self.assertEqual(extract_gemini_image_assets(payload), [])

    def test_gco_short_link_is_recognized_and_canonicalized(self):
        short_url = "https://g.co/gemini/share/abc123"

        self.assertTrue(is_gemini_share_url(short_url))
        self.assertEqual(
            canonical_gemini_share_url(short_url),
            "https://gemini.google.com/share/abc123",
        )

    def test_download_uses_original_resolution_url(self):
        output = BytesIO()
        Image.new("RGB", (4, 3), color=(12, 34, 56)).save(
            output,
            format="PNG",
        )
        requested_urls = []

        class Client:
            def request(self, url, **kwargs):
                requested_urls.append(url)
                return HttpResponse(
                    body=output.getvalue(),
                    content_type="image/png",
                    final_url=url,
                )

        asset = GeminiImageAsset(
            url="https://lh3.googleusercontent.com/generated=mp2",
            filename="generated.png",
            declared_type="image/png",
            width=1024,
            height=768,
            kind="generated",
            turn_index=0,
            position=0,
            caption="Illustration",
        )

        downloaded = download_gemini_image(
            asset,
            client=Client(),
            source_url="https://gemini.google.com/share/abc123",
        )

        self.assertEqual(
            requested_urls,
            ["https://lh3.googleusercontent.com/generated=s0"],
        )
        self.assertEqual(downloaded.extension, "png")


class GeminiIllustrationImportTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.settings_override.enable()
        self.author = get_user_model().objects.create_user(
            username="gemini-author",
            password="password",
        )
        self.section = Section.objects.create(
            name="Gemini",
            slug="gemini-import",
        )
        self.dialogue = Dialogue.objects.create(
            title="Gemini images",
            section=self.section,
            source_url="https://gemini.google.com/share/test-share",
            human_author=self.author,
            status=Dialogue.STATUS_SUBMITTED,
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def png_bytes(self):
        output = BytesIO()
        Image.new("RGB", (2, 2), color=(12, 34, 56)).save(output, format="PNG")
        return output.getvalue()

    def test_import_saves_image_and_is_idempotent_by_content(self):
        record = [
            None,
            1,
            "generated.png",
            "https://lh3.googleusercontent.com/generated=mp2",
            None,
            "asset-token",
            None,
            None,
            2,
            [1_700_000_000, 0],
            None,
            "image/png",
            None,
            None,
            None,
            [1024, 768, 1000],
        ]
        payload = [[None, [[None, None, [["Draw it"]], [[record]]]]]]
        image_bytes = self.png_bytes()
        downloaded = DownloadedImage(
            body=image_bytes,
            extension="png",
            digest=hashlib.sha256(image_bytes).hexdigest(),
        )

        with (
            patch(
                "dialogues.gemini_illustrations.fetch_gemini_payload",
                return_value=(
                    "test-share",
                    self.dialogue.source_url,
                    payload,
                ),
            ),
            patch(
                "dialogues.gemini_illustrations.download_gemini_image",
                return_value=downloaded,
            ) as downloader,
        ):
            first = import_gemini_illustrations(self.dialogue)
            second = import_gemini_illustrations(self.dialogue)

        self.assertEqual(first.imported, 1)
        self.assertEqual(second.imported, 0)
        self.assertEqual(second.skipped_duplicates, 1)
        illustration = DialogueIllustration.objects.get(dialogue=self.dialogue)
        self.assertIn("Draw it", illustration.caption)
        self.assertEqual(
            illustration.source_key,
            "gemini:test-share:0:generated:0",
        )
        downloader.assert_called_once()


class DialogueModerationTests(APITestCase):
    def setUp(self):
        self.moderator = get_user_model().objects.create_user(
            username='moderator',
            password='password',
            is_staff=True,
        )
        self.author = get_user_model().objects.create_user(
            username='author',
            password='password',
        )
        section = Section.objects.create(name='Section', slug='moderation-section')
        self.dialogue = Dialogue.objects.create(
            title='Submitted dialogue',
            section=section,
            text='Text',
            human_author=self.author,
            status=Dialogue.STATUS_SUBMITTED,
        )
        self.client.force_authenticate(user=self.moderator)

    def test_request_changes_allows_empty_moderation_note(self):
        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/moderate/',
            {'status': Dialogue.STATUS_CHANGES_REQUESTED, 'moderation_note': ''},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.status, Dialogue.STATUS_CHANGES_REQUESTED)
        self.assertEqual(self.dialogue.moderation_note, '')

    def test_request_changes_saves_moderation_note(self):
        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/moderate/',
            {
                'status': Dialogue.STATUS_CHANGES_REQUESTED,
                'moderation_note': 'Clarify the second argument.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.status, Dialogue.STATUS_CHANGES_REQUESTED)
        self.assertEqual(self.dialogue.moderation_note, 'Clarify the second argument.')

    def test_publication_requires_external_link_or_text(self):
        self.dialogue.text = ''
        self.dialogue.save(update_fields=['text', 'published', 'updated_at'])
        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/moderate/',
            {'status': Dialogue.STATUS_PUBLISHED, 'moderation_note': ''},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.status, Dialogue.STATUS_SUBMITTED)

    def test_dialogue_with_external_link_can_be_published(self):
        self.dialogue.source_url = 'https://chatgpt.com/share/example'
        self.dialogue.save(update_fields=['source_url', 'published', 'updated_at'])

        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/moderate/',
            {'status': Dialogue.STATUS_PUBLISHED, 'moderation_note': ''},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.status, Dialogue.STATUS_PUBLISHED)
        self.assertTrue(self.dialogue.published)

    def test_dialogue_with_pasted_text_can_be_published(self):
        response = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/moderate/',
            {'status': Dialogue.STATUS_PUBLISHED, 'moderation_note': ''},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.status, Dialogue.STATUS_PUBLISHED)


class ExternalDialogueLinkTests(APITestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username='author-link',
            first_name='Ada',
            last_name='Lovelace',
            password='password',
        )
        self.section = Section.objects.create(name='Links', slug='links')
        self.client.force_authenticate(user=self.author)

    def test_submitted_dialogue_requires_external_link_or_text(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Missing link',
            'section': self.section.id,
            'status': Dialogue.STATUS_SUBMITTED,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.data)

    def test_pasted_dialogue_can_be_submitted_without_external_link(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Pasted dialogue',
            'section': self.section.id,
            'text': '## Author\n\nQuestion\n\n## AI\n\nAnswer',
            'status': Dialogue.STATUS_SUBMITTED,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        dialogue = Dialogue.objects.get(pk=response.data['id'])
        self.assertEqual(dialogue.source_url, '')
        self.assertIn('Question', dialogue.text)

    def test_external_link_adds_human_and_source_model_authors(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Gemini dialogue',
            'section': self.section.id,
            'source_url': 'https://share.google/aimode/example',
            'summary': '',
            'status': Dialogue.STATUS_SUBMITTED,
            'authors': [{'kind': 'person', 'name': 'Coauthor'}],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        dialogue = Dialogue.objects.get(pk=response.data['id'])
        self.assertEqual(dialogue.source_url, 'https://share.google/aimode/example')
        self.assertEqual(dialogue.llm_name, 'Gemini')
        self.assertEqual(
            [(author['kind'], author['name']) for author in dialogue.authors],
            [('person', 'Ada Lovelace'), ('person', 'Coauthor'), ('ai_model', 'Gemini')],
        )

    def test_private_external_link_is_rejected(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Private link',
            'section': self.section.id,
            'source_url': 'http://127.0.0.1/share/example',
            'status': Dialogue.STATUS_SUBMITTED,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('source_url', response.data)

    def test_share_google_can_be_imported(self):
        extractor = SimpleNamespace(extract_share=lambda url: {
            'service': 'gemini',
            'title': 'Imported title',
            'messages': [
                {'role': 'user', 'content': 'Question'},
                {'role': 'assistant', 'content': 'Answer'},
            ],
        })
        with patch.dict('sys.modules', {'llm_shared_chat': extractor}):
            response = self.client.post('/api/dialogues/import-share/', {
                'url': 'https://share.google/aimode/example',
            }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['service'], 'gemini')
        self.assertIn('Question', response.data['markdown'])

    def test_gco_gemini_link_is_canonicalized_for_import(self):
        imported_urls = []

        def extract_share(url):
            imported_urls.append(url)
            return {
                'service': 'gemini',
                'title': 'Imported title',
                'messages': [
                    {'role': 'user', 'content': 'Question'},
                    {'role': 'assistant', 'content': 'Answer'},
                ],
            }

        extractor = SimpleNamespace(extract_share=extract_share)
        with patch.dict('sys.modules', {'llm_shared_chat': extractor}):
            response = self.client.post('/api/dialogues/import-share/', {
                'url': 'https://g.co/gemini/share/abc123',
            }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            imported_urls,
            ['https://gemini.google.com/share/abc123'],
        )

    def test_gco_gemini_link_sets_gemini_as_source_model(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Gemini short link',
            'section': self.section.id,
            'source_url': 'https://g.co/gemini/share/abc123',
            'status': Dialogue.STATUS_DRAFT,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        dialogue = Dialogue.objects.get(pk=response.data['id'])
        self.assertEqual(dialogue.llm_name, 'Gemini')

    def test_gemini_illustrations_are_imported_when_draft_is_submitted(self):
        import_result = GeminiIllustrationImportResult(
            found=2,
            imported=2,
            skipped_duplicates=0,
            failed=0,
        )
        with patch(
            'dialogues.views.import_gemini_illustrations',
            return_value=import_result,
        ) as importer:
            create_response = self.client.post('/api/dialogues/', {
                'title': 'Gemini draft',
                'section': self.section.id,
                'source_url': 'https://gemini.google.com/share/example',
                'status': Dialogue.STATUS_DRAFT,
            }, format='json')
            submit_response = self.client.patch(
                f"/api/dialogues/{create_response.data['id']}/",
                {'status': Dialogue.STATUS_SUBMITTED},
                format='json',
            )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(submit_response.status_code, 200)
        importer.assert_called_once()
        self.assertTrue(AuditLog.objects.filter(
            action='import_gemini_illustrations',
            object_id=str(create_response.data['id']),
        ).exists())

    def test_gemini_import_failure_does_not_block_submission(self):
        with (
            patch(
                'dialogues.views.import_gemini_illustrations',
                side_effect=RuntimeError('Temporary Gemini failure'),
            ),
            patch('dialogues.views.logger.exception'),
        ):
            response = self.client.post('/api/dialogues/', {
                'title': 'Gemini dialogue',
                'section': self.section.id,
                'source_url': 'https://gemini.google.com/share/example',
                'status': Dialogue.STATUS_SUBMITTED,
            }, format='json')

        self.assertEqual(response.status_code, 201)
        dialogue = Dialogue.objects.get(pk=response.data['id'])
        self.assertEqual(dialogue.status, Dialogue.STATUS_SUBMITTED)
        self.assertTrue(AuditLog.objects.filter(
            action='import_gemini_illustrations_failed',
            object_id=str(dialogue.id),
        ).exists())


class SolarisDialogueContextTests(APITestCase):
    def test_context_contains_all_and_only_published_dialogues(self):
        section = Section.objects.create(name='Context', slug='context')
        published = Dialogue.objects.create(
            title='Public knowledge',
            section=section,
            source_url='https://chatgpt.com/share/public',
            text='Useful public dialogue',
            status=Dialogue.STATUS_PUBLISHED,
            authors=[{'kind': 'ai_model', 'name': 'ChatGPT'}],
        )
        Dialogue.objects.create(
            title='Private draft',
            section=section,
            text='Secret draft',
            status=Dialogue.STATUS_DRAFT,
        )

        response = self.client.get('/api/dialogues/context/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['dialogue_count'], 1)
        self.assertEqual(response.data['dialogues'][0]['id'], published.id)
        self.assertIn('Useful public dialogue', response.data['markdown'])
        self.assertNotIn('Secret draft', response.data['markdown'])
