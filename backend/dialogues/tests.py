from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from types import SimpleNamespace
from unittest.mock import patch

from .models import Dialogue, DialogueInlineImage, Section


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
