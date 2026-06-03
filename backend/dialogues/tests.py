from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Dialogue, Section


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
