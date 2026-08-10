import hashlib
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
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
    extract_gemini_recommended_literature,
    import_gemini_illustrations,
    is_gemini_share_url,
)
from .models import (
    AuditLog, Dialogue, DialogueIllustration, DialogueInlineImage,
    DialogueResourceProposal, Section,
)


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

    def test_extracts_largest_retrieval_preview_once(self):
        small_preview = (
            "https://encrypted-tbn3.gstatic.com/images?q=small-preview"
        )
        large_preview = (
            "https://encrypted-tbn3.gstatic.com/images?q=large-preview"
        )
        retrieval_group = [
            [[
                "https://upload.wikimedia.org/wikipedia/commons/e/e1/"
                "Flag_of_Ukraine.svg"
            ], None, 1200, 800, "flag of Ukraine", None, "image-id"],
            [["https://commons.wikimedia.org/wiki/File:Flag_of_Ukraine.svg"],
             "commons.wikimedia.org", 5,
             "https://encrypted-tbn0.gstatic.com/favicon-tbn?q=favicon"],
            None,
            [[small_preview], None, 250, 200],
            None,
            None,
            None,
            [
                "http://googleusercontent.com/image_collection/"
                "image_retrieval/result_0",
                None,
                "flag of Ukraine",
                None,
                None,
                1,
            ],
            None,
            None,
            None,
            None,
            [[large_preview], None, 678, 452],
        ]
        payload = [[
            None,
            [[
                None,
                None,
                [["Прапор України"]],
                [["Response", retrieval_group], [retrieval_group]],
            ]],
        ]]

        assets = extract_gemini_image_assets(payload)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].kind, "retrieved")
        self.assertEqual(assets[0].url, large_preview)
        self.assertEqual((assets[0].width, assets[0].height), (678, 452))
        self.assertIn("flag of Ukraine", assets[0].caption)

    def test_uses_inline_caption_for_image_agent_retrieval(self):
        preview = "https://encrypted-tbn0.gstatic.com/images?q=coat-of-arms"
        retrieval_group = [
            [[
                "https://upload.wikimedia.org/wikipedia/commons/c/cf/"
                "Coat_of_Arms_of_Ukraine.svg"
            ], None, 660, 922],
            None,
            None,
            [[preview], None, 267, 374],
            None,
            None,
            None,
            [
                "http://googleusercontent.com/image_agent_tag_12345",
                None,
                "Coat of arms of Ukraine",
                None,
                None,
                1,
            ],
        ]
        response = (
            '<Image alt="Герб України" caption="Малий Державний Герб України" '
            'src="image_agent_tag_12345"/>'
        )
        payload = [[
            None,
            [[None, None, [["Покажи герб"]], [[response], retrieval_group]]],
        ]]

        assets = extract_gemini_image_assets(payload)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].url, preview)
        self.assertIn("Малий Державний Герб України", assets[0].caption)

    def test_retrieval_does_not_download_arbitrary_external_host(self):
        retrieval_group = [
            [["https://example.com/image.png"], None, 1000, 800],
            [
                "http://googleusercontent.com/image_collection/"
                "image_retrieval/result_0",
                None,
                "External image",
            ],
        ]
        payload = [[
            None,
            [[None, None, [["Prompt"]], [retrieval_group]]],
        ]]

        self.assertEqual(extract_gemini_image_assets(payload), [])

    def test_extracts_last_explicit_recommended_literature_block(self):
        payload = [[
            None,
            [
                [
                    None,
                    None,
                    [["First prompt"]],
                    ["## Recommended reading\n\n- Older source"],
                ],
                [
                    None,
                    None,
                    [["Second prompt"]],
                    [
                        "Висновок.\n\n"
                        "## Рекомендована література\n\n"
                        "- Автор. Нова книга. 2025.\n\n"
                        "### Першоджерела\n\n"
                        "- Автор. Стаття. DOI: 10.1000/example\n\n"
                        "## Наступний розділ\n\n"
                        "Цей текст не належить до літератури."
                    ],
                ],
            ],
        ]]

        literature = extract_gemini_recommended_literature(payload)

        self.assertEqual(
            literature,
            "- Автор. Нова книга. 2025.\n\n"
            "### Першоджерела\n\n"
            "- Автор. Стаття. DOI: 10.1000/example",
        )

    def test_does_not_treat_unlabelled_citations_as_literature(self):
        payload = [[
            None,
            [[
                None,
                None,
                [["Prompt"]],
                [
                    "Джерело: https://example.com/article\n\n"
                    "Див. також книгу автора.\n\n"
                    "У відповіді використані джерела та література.\n"
                    "Recommended reading can help explore the topic."
                ],
            ]],
        ]]

        self.assertEqual(extract_gemini_recommended_literature(payload), "")

    def test_extracts_common_literature_heading_variants(self):
        headings = (
            "## Рекомендованная литература",
            "### Список літератури",
            "**Рекомендовані джерела:**",
            "4. Джерела та література",
            "📚 Додаткова література",
            "## Список використаних джерел",
            "# Список источников",
            "### Рекомендованная литература и источники",
            "__Для дальнейшего чтения__:",
            "## Further reading",
            "## Reading list",
            "### Recommended resources",
            "### References",
            "2. **Works cited:**",
            "## Sources (selected)",
        )

        for heading in headings:
            with self.subTest(heading=heading):
                payload = [[
                    None,
                    [[
                        None,
                        None,
                        [["Prompt"]],
                        [f"{heading}\n\n- Source"],
                    ]],
                ]]

                self.assertEqual(
                    extract_gemini_recommended_literature(payload),
                    "- Source",
                )

    def test_gco_short_link_is_recognized_and_canonicalized(self):
        short_url = "https://g.co/gemini/share/abc123"

        self.assertTrue(is_gemini_share_url(short_url))
        self.assertEqual(
            canonical_gemini_share_url(short_url),
            "https://gemini.google.com/share/abc123",
        )

    def test_share_gemini_short_link_is_resolved_and_canonicalized(self):
        short_url = "https://share.gemini.google/6bz7OD5NL7wx"
        requested_urls = []

        class Client:
            def request(self, url, **kwargs):
                requested_urls.append(url)
                return HttpResponse(
                    body=b"",
                    content_type="text/html",
                    final_url=(
                        "https://gemini.google.com/share/a89ae81075ef"
                        "?skid=example"
                    ),
                )

        self.assertTrue(is_gemini_share_url(short_url))
        self.assertEqual(
            canonical_gemini_share_url(short_url, client=Client()),
            "https://gemini.google.com/share/a89ae81075ef",
        )
        self.assertEqual(requested_urls, [short_url])

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

    def test_download_keeps_retrieval_preview_url_unchanged(self):
        output = BytesIO()
        Image.new("RGB", (4, 3), color=(12, 34, 56)).save(
            output,
            format="PNG",
        )
        preview_url = "https://encrypted-tbn0.gstatic.com/images?q=preview"
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
            url=preview_url,
            filename="retrieved.img",
            declared_type="",
            width=400,
            height=300,
            kind="retrieved",
            turn_index=0,
            position=0,
            caption="Retrieved image",
        )

        downloaded = download_gemini_image(
            asset,
            client=Client(),
            source_url="https://gemini.google.com/share/abc123",
        )

        self.assertEqual(requested_urls, [preview_url])
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

    def test_import_saves_explicit_recommended_literature(self):
        payload = [[None, [[
            None,
            None,
            [["Recommend sources"]],
            [
                "## Рекомендуемая литература\n\n"
                "- Автор. Книга. 2024. https://example.com/book"
            ],
        ]]]]

        with patch(
            "dialogues.gemini_illustrations.fetch_gemini_payload",
            return_value=(
                "test-share",
                self.dialogue.source_url,
                payload,
            ),
        ):
            result = import_gemini_illustrations(self.dialogue)

        self.dialogue.refresh_from_db()
        self.assertEqual(
            self.dialogue.recommended_literature,
            "- Автор. Книга. 2024. https://example.com/book",
        )
        self.assertTrue(result.literature_found)
        self.assertTrue(result.literature_imported)
        self.assertEqual(result.found, 0)

    def test_import_does_not_overwrite_existing_recommended_literature(self):
        self.dialogue.recommended_literature = "Авторський список"
        self.dialogue.save(update_fields=["recommended_literature", "updated_at"])
        payload = [[None, [[
            None,
            None,
            [["Recommend sources"]],
            ["## Recommended reading\n\n- Replacement source"],
        ]]]]

        with patch(
            "dialogues.gemini_illustrations.fetch_gemini_payload",
            return_value=(
                "test-share",
                self.dialogue.source_url,
                payload,
            ),
        ):
            result = import_gemini_illustrations(self.dialogue)

        self.dialogue.refresh_from_db()
        self.assertEqual(
            self.dialogue.recommended_literature,
            "Авторський список",
        )
        self.assertTrue(result.literature_found)
        self.assertFalse(result.literature_imported)


class GeminiIllustrationBackfillCommandTests(APITestCase):
    def setUp(self):
        self.section = Section.objects.create(
            name="Backfill",
            slug="gemini-backfill",
        )

    def create_dialogue(
        self,
        title,
        *,
        source_url="https://gemini.google.com/share/example",
        status=Dialogue.STATUS_PUBLISHED,
    ):
        return Dialogue.objects.create(
            title=title,
            section=self.section,
            source_url=source_url,
            status=status,
        )

    def test_dry_run_lists_only_published_gemini_dialogues_missing_content(self):
        eligible = self.create_dialogue(
            "Eligible dialogue",
            source_url="https://share.gemini.google/6bz7OD5NL7wx",
        )
        with_images = self.create_dialogue("Already illustrated")
        with_images.recommended_literature = "Existing literature"
        with_images.save(
            update_fields=["recommended_literature", "updated_at"]
        )
        DialogueIllustration.objects.create(
            dialogue=with_images,
            image="illustrations/existing.png",
        )
        without_literature = self.create_dialogue(
            "Illustrated without literature"
        )
        DialogueIllustration.objects.create(
            dialogue=without_literature,
            image="illustrations/other.png",
        )
        self.create_dialogue(
            "Not Gemini",
            source_url="https://example.com/dialogue",
        )
        self.create_dialogue(
            "Still submitted",
            status=Dialogue.STATUS_SUBMITTED,
        )
        stdout = StringIO()

        with patch(
            "dialogues.management.commands.backfill_gemini_illustrations."
            "import_gemini_illustrations"
        ) as importer:
            call_command(
                "backfill_gemini_illustrations",
                "--dry-run",
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn(f"[{eligible.pk}] Eligible dialogue", output)
        self.assertIn(
            f"[{without_literature.pk}] Illustrated without literature",
            output,
        )
        self.assertNotIn("Already illustrated", output)
        self.assertNotIn("Not Gemini", output)
        self.assertNotIn("Still submitted", output)
        importer.assert_not_called()
        self.assertFalse(AuditLog.objects.exists())

    def test_imports_eligible_dialogue_and_writes_audit_log(self):
        dialogue = self.create_dialogue("Needs images")
        result = GeminiIllustrationImportResult(
            found=2,
            imported=2,
            skipped_duplicates=0,
            failed=0,
            literature_found=True,
            literature_imported=True,
        )
        stdout = StringIO()

        with patch(
            "dialogues.management.commands.backfill_gemini_illustrations."
            "import_gemini_illustrations",
            return_value=result,
        ) as importer:
            call_command("backfill_gemini_illustrations", stdout=stdout)

        self.assertEqual(importer.call_count, 1)
        self.assertEqual(importer.call_args.args[0].pk, dialogue.pk)
        self.assertIn("imported images: 2", stdout.getvalue())
        self.assertIn("imported literature: 1", stdout.getvalue())
        audit = AuditLog.objects.get(
            action="backfill_gemini_illustrations",
            object_id=str(dialogue.pk),
        )
        self.assertIn("imported: 2", audit.details)
        self.assertIn("literature imported: True", audit.details)

    def test_continues_after_one_dialogue_fails(self):
        first = self.create_dialogue("Broken link")
        second = self.create_dialogue(
            "Working link",
            source_url="https://gemini.google.com/share/working",
        )
        result = GeminiIllustrationImportResult(
            found=1,
            imported=1,
            skipped_duplicates=0,
            failed=0,
        )

        with patch(
            "dialogues.management.commands.backfill_gemini_illustrations."
            "import_gemini_illustrations",
            side_effect=[RuntimeError("Unavailable share"), result],
        ) as importer:
            with self.assertRaises(CommandError):
                call_command(
                    "backfill_gemini_illustrations",
                    stdout=StringIO(),
                    stderr=StringIO(),
                )

        self.assertEqual(importer.call_count, 2)
        self.assertEqual(importer.call_args_list[0].args[0].pk, first.pk)
        self.assertEqual(importer.call_args_list[1].args[0].pk, second.pk)
        self.assertTrue(
            AuditLog.objects.filter(
                action="backfill_gemini_illustrations_failed",
                object_id=str(first.pk),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="backfill_gemini_illustrations",
                object_id=str(second.pk),
            ).exists()
        )


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

    def test_share_gemini_link_is_allowed_and_canonicalized_for_import(self):
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
        with (
            patch.dict('sys.modules', {'llm_shared_chat': extractor}),
            patch(
                'dialogues.views.canonical_gemini_share_url',
                return_value='https://gemini.google.com/share/a89ae81075ef',
            ) as canonicalizer,
        ):
            response = self.client.post('/api/dialogues/import-share/', {
                'url': 'https://share.gemini.google/6bz7OD5NL7wx',
            }, format='json')

        self.assertEqual(response.status_code, 200)
        canonicalizer.assert_called_once_with(
            'https://share.gemini.google/6bz7OD5NL7wx'
        )
        self.assertEqual(
            imported_urls,
            ['https://gemini.google.com/share/a89ae81075ef'],
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

    def test_share_gemini_link_sets_gemini_as_source_model(self):
        response = self.client.post('/api/dialogues/', {
            'title': 'Gemini redirect link',
            'section': self.section.id,
            'source_url': 'https://share.gemini.google/6bz7OD5NL7wx',
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

    def test_staff_short_link_is_imported_when_published_immediately(self):
        self.author.is_staff = True
        self.author.save(update_fields=['is_staff'])
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
                'title': 'Staff Gemini draft',
                'section': self.section.id,
                'source_url': 'https://share.gemini.google/6bz7OD5NL7wx',
                'status': Dialogue.STATUS_DRAFT,
            }, format='json')
            publish_response = self.client.patch(
                f"/api/dialogues/{create_response.data['id']}/",
                {'status': Dialogue.STATUS_SUBMITTED},
                format='json',
            )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(publish_response.status_code, 200)
        self.assertEqual(publish_response.data['status'], Dialogue.STATUS_PUBLISHED)
        importer.assert_called_once()

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


@override_settings(MEDIA_ROOT='/tmp/solaris-resource-proposal-test-media')
class DialogueResourceProposalTests(APITestCase):
    image_bytes = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
        b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username='proposal-author',
            password='password',
        )
        self.other_user = get_user_model().objects.create_user(
            username='proposal-other',
            password='password',
        )
        self.moderator = get_user_model().objects.create_user(
            username='proposal-moderator',
            password='password',
            is_staff=True,
        )
        self.section = Section.objects.create(name='Resources', slug='resources')
        self.dialogue = Dialogue.objects.create(
            title='Published resources',
            section=self.section,
            text='Text',
            human_author=self.author,
            status=Dialogue.STATUS_PUBLISHED,
            authors=[
                {'kind': 'person', 'name': 'Existing author'},
                {'kind': 'ai_model', 'name': 'Gemini', 'version': '2.5'},
            ],
            llm_name='Gemini',
            llm_version='2.5',
            recommended_literature='Existing book',
        )

    def submit(self, data, *, user=None, format='json'):
        self.client.force_authenticate(user=user or self.author)
        return self.client.post(
            f'/api/dialogues/{self.dialogue.id}/resource-proposals/',
            data,
            format=format,
        )

    def moderate(self, proposal, action='approve', *, user=None):
        self.client.force_authenticate(user=user or self.moderator)
        return self.client.post(
            f'/api/resource-proposals/{proposal.id}/moderate/',
            {'action': action},
            format='json',
        )

    def image(self):
        return SimpleUploadedFile('proposal.gif', self.image_bytes, content_type='image/gif')

    def test_authenticated_user_can_submit_each_resource_type(self):
        responses = [
            self.submit({
                'resource_type': 'author',
                'kind': 'organization',
                'name': 'Solaris Institute',
                'description': 'Research group',
            }),
            self.submit({
                'resource_type': 'ai_model',
                'name': 'Claude',
                'version': '4',
            }),
            self.submit({
                'resource_type': 'literature',
                'text': 'New book',
            }),
            self.submit({
                'resource_type': 'illustration',
                'caption': 'Diagram',
                'image': self.image(),
            }, format='multipart'),
        ]

        self.assertEqual([response.status_code for response in responses], [201, 201, 201, 201])
        self.assertEqual(DialogueResourceProposal.objects.count(), 4)
        self.assertTrue(all(
            proposal.status == DialogueResourceProposal.STATUS_PENDING
            for proposal in DialogueResourceProposal.objects.all()
        ))
        self.assertEqual(responses[0].data['payload']['kind'], 'organization')
        self.assertEqual(responses[1].data['payload']['kind'], 'ai_model')
        self.assertIn('/media/resource_proposals/illustrations/', responses[3].data['image'])

    def test_submission_requires_authentication_and_published_dialogue(self):
        self.client.force_authenticate(user=None)
        unauthenticated = self.client.post(
            f'/api/dialogues/{self.dialogue.id}/resource-proposals/',
            {'resource_type': 'literature', 'text': 'Book'},
            format='json',
        )
        self.assertEqual(unauthenticated.status_code, 401)

        self.dialogue.status = Dialogue.STATUS_DRAFT
        self.dialogue.save(update_fields=['status', 'published', 'updated_at'])
        unpublished = self.submit({'resource_type': 'literature', 'text': 'Book'})
        self.assertEqual(unpublished.status_code, 404)

    def test_submission_validates_type_specific_fields(self):
        cases = [
            ({'resource_type': 'author'}, 'name'),
            ({'resource_type': 'ai_model'}, 'name'),
            ({'resource_type': 'literature'}, 'text'),
            ({'resource_type': 'illustration'}, 'image'),
        ]
        for body, field in cases:
            with self.subTest(resource_type=body['resource_type']):
                response = self.submit(body)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_user_sees_only_their_own_pending_proposals(self):
        own = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Own'},
            submitted_by=self.author,
        )
        DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Other'},
            submitted_by=self.other_user,
        )
        DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Reviewed'},
            submitted_by=self.author,
            status=DialogueResourceProposal.STATUS_APPROVED,
        )

        self.client.force_authenticate(user=self.author)
        response = self.client.get(
            f'/api/dialogues/{self.dialogue.id}/resource-proposals/'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['results']], [own.id])

    def test_moderator_queue_can_filter_by_resource_type(self):
        author = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_AUTHOR,
            payload={'kind': 'person', 'name': 'Author'},
            submitted_by=self.author,
        )
        DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Book'},
            submitted_by=self.author,
        )

        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(
            '/api/resource-proposals/review/',
            {'resource_type': 'author'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['results']], [author.id])
        self.assertEqual(response.data['results'][0]['dialogue_title'], self.dialogue.title)

    def test_approving_author_adds_it_without_duplicate(self):
        proposal = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_AUTHOR,
            payload={
                'kind': 'organization',
                'name': 'Solaris Institute',
                'version': '',
                'description': 'Research group',
            },
            submitted_by=self.author,
        )

        response = self.moderate(proposal)
        duplicate = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_AUTHOR,
            payload=proposal.payload,
            submitted_by=self.other_user,
        )
        duplicate_response = self.moderate(duplicate)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(duplicate_response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(
            [author['name'] for author in self.dialogue.authors].count('Solaris Institute'),
            1,
        )
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, DialogueResourceProposal.STATUS_APPROVED)
        self.assertEqual(proposal.reviewed_by, self.moderator)

    def test_approving_additional_ai_models_keeps_source_model(self):
        for name, version in [('Claude', '4'), ('ChatGPT', '5')]:
            proposal = DialogueResourceProposal.objects.create(
                dialogue=self.dialogue,
                resource_type=DialogueResourceProposal.RESOURCE_AI_MODEL,
                payload={
                    'kind': 'ai_model',
                    'name': name,
                    'version': version,
                    'description': '',
                },
                submitted_by=self.author,
            )
            self.assertEqual(self.moderate(proposal).status_code, 200)

        self.dialogue.refresh_from_db()
        model_names = [
            author['name']
            for author in self.dialogue.authors
            if author.get('kind') == 'ai_model'
        ]
        self.assertEqual(model_names, ['Gemini', 'Claude', 'ChatGPT'])
        self.assertEqual(self.dialogue.llm_name, 'Gemini')
        self.assertEqual(self.dialogue.llm_version, '2.5')

    def test_approving_literature_appends_a_separate_item(self):
        proposal = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'New book'},
            submitted_by=self.author,
        )

        response = self.moderate(proposal)

        self.assertEqual(response.status_code, 200)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.recommended_literature, 'Existing book\n\nNew book')

    def test_approving_illustration_creates_plain_dialogue_illustration(self):
        response = self.submit({
            'resource_type': 'illustration',
            'caption': 'User diagram',
            'image': self.image(),
        }, format='multipart')
        proposal = DialogueResourceProposal.objects.get(pk=response.data['id'])

        moderated = self.moderate(proposal)

        self.assertEqual(moderated.status_code, 200)
        illustration = DialogueIllustration.objects.get(dialogue=self.dialogue)
        self.assertEqual(illustration.caption, 'User diagram')
        self.assertEqual(illustration.source_key, '')
        self.assertEqual(illustration.image.name, proposal.image.name)

    def test_rejection_does_not_change_dialogue_and_proposal_cannot_be_reviewed_twice(self):
        proposal = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Rejected book'},
            submitted_by=self.author,
        )

        rejected = self.moderate(proposal, 'reject')
        reviewed_again = self.moderate(proposal, 'approve')

        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(reviewed_again.status_code, 400)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.recommended_literature, 'Existing book')
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, DialogueResourceProposal.STATUS_REJECTED)
        self.assertTrue(AuditLog.objects.filter(
            action='reject_resource_proposal',
            object_id=str(proposal.id),
        ).exists())

    def test_non_staff_user_cannot_moderate(self):
        proposal = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Book'},
            submitted_by=self.author,
        )

        response = self.moderate(proposal, user=self.other_user)

        self.assertEqual(response.status_code, 403)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, DialogueResourceProposal.STATUS_PENDING)

    def test_proposal_cannot_be_approved_after_dialogue_is_unpublished(self):
        proposal = DialogueResourceProposal.objects.create(
            dialogue=self.dialogue,
            resource_type=DialogueResourceProposal.RESOURCE_LITERATURE,
            payload={'text': 'Book'},
            submitted_by=self.author,
        )
        self.dialogue.status = Dialogue.STATUS_ARCHIVED
        self.dialogue.save(update_fields=['status', 'published', 'updated_at'])

        response = self.moderate(proposal)

        self.assertEqual(response.status_code, 400)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, DialogueResourceProposal.STATUS_PENDING)
        self.dialogue.refresh_from_db()
        self.assertEqual(self.dialogue.recommended_literature, 'Existing book')


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
