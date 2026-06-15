from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

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
