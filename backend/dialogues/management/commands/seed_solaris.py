from django.core.management.base import BaseCommand

from dialogues.models import Interlocutor, Section


SECTIONS = [
    {
        'name': 'Світогляд',
        'slug': 'worldview-ai',
        'brief': (
            'Діалоги про світогляд у контексті ШІ: анімізм, релігія, наука, '
            'штучний інтелект як можливий новий спосіб опису світу.'
        ),
        'order': 10,
    },
    {
        'name': 'Теорія пізнання',
        'slug': 'epistemology-ai',
        'brief': (
            'Питання знання, істини, досвіду, апріорного та меж пізнання у порівнянні '
            'з великими мовними моделями й агентами.'
        ),
        'order': 20,
    },
    {
        'name': 'Навчання',
        'slug': 'learning-ai',
        'brief': (
            'Маєвтика, евристика, самоосвіта та спільне проєктування знання '
            'людиною і ШІ.'
        ),
        'order': 30,
    },
    {
        'name': 'Психологія',
        'slug': 'psychology-ai',
        'brief': (
            'Психологічні теорії, мислення, сприйняття та поведінка людини у звʼязку '
            'з LLM і когнітивними технологіями.'
        ),
        'order': 40,
    },
    {
        'name': 'Технології ШІ',
        'slug': 'ai-technologies',
        'brief': (
            'Технологічний бік штучного інтелекту: LLM, агенти, інструменти, '
            'обмеження та практики використання.'
        ),
        'order': 50,
    },
    {
        'name': 'Мова, логіка',
        'slug': 'language-logic-ai',
        'brief': (
            'Формальна логіка, мова, сенс, аргументація та роль мовних моделей '
            'у роботі із символічними структурами.'
        ),
        'order': 60,
    },
    {
        'name': 'Евристика',
        'slug': 'heuristics-ai',
        'brief': (
            'Правдоподібні міркування, стратегії пошуку рішень, творче мислення '
            'та ШІ як інтелектуальний партнер.'
        ),
        'order': 70,
    },
    {
        'name': 'Когнітивна еволюція',
        'slug': 'cognitive-evolution',
        'brief': (
            'Діалоги про те, як людина і ШІ змінюють процеси пізнання, мислення '
            'та культурного відбору ідей.'
        ),
        'order': 80,
    },
]


INTERLOCUTORS = [
    {
        'name': 'Сократ',
        'description': (
            'Давньогрецький філософ, повʼязаний із діалогічним методом, маєвтикою '
            'та розумінням знання як результату питання і суперечки.'
        ),
    },
    {
        'name': 'Платон',
        'description': (
            'Філософ античності, автор учення про світ ідей і діалогів, важливих для теми '
            'обʼєктивованого знання.'
        ),
    },
    {
        'name': 'Аристотель',
        'description': (
            'Філософ і систематизатор знання; важливий для тем логіки, категорій, причинності '
            'та структури наукового пояснення.'
        ),
    },
    {
        'name': 'Френсіс Бекон',
        'description': (
            'Філософ Нового часу, повʼязаний з емпіризмом, індукцією та програмою '
            'організації наукового знання.'
        ),
    },
    {
        'name': 'Рене Декарт',
        'description': (
            'Філософ раціоналізму; важливий для тем методу, сумніву, свідомості й підстав '
            'достовірного знання.'
        ),
    },
    {
        'name': 'Джон Лок',
        'description': (
            'Представник емпіризму; важливий для обговорення досвіду, ідей і походження '
            'людського знання.'
        ),
    },
    {
        'name': 'Девід Юм',
        'description': (
            'Філософ емпіризму і скептицизму; важливий для тем причинності, індукції '
            'та меж раціонального висновку.'
        ),
    },
    {
        'name': 'Готфрід Лейбніц',
        'description': (
            'Філософ і математик; важливий для тем раціоналізму, можливих світів, символічного '
            'мислення та універсального числення.'
        ),
    },
    {
        'name': 'Иммануил Кант',
        'description': (
            'Філософ критичної теорії пізнання; ключова фігура для тем апріорного знання, '
            'умов досвіду та меж розуму.'
        ),
    },
    {
        'name': 'Чарльз Пірс',
        'description': (
            'Філософ, логік і засновник прагматизму; важливий для тем знаків, абдукції '
            'та дослідницького процесу.'
        ),
    },
    {
        'name': 'Эрнст Мах',
        'description': (
            'Фізик і філософ науки; важливий для тем досвіду, економії мислення та критики '
            'метафізичних передумов.'
        ),
    },
    {
        'name': 'Карл Поппер',
        'description': (
            'Філософ науки; важливий для тем фальсифікованості, еволюційної епістемології '
            'та третього світу обʼєктивного знання.'
        ),
    },
    {
        'name': 'Зиґмунд Фройд',
        'description': (
            'Засновник психоаналізу; у специфікації згадується у звʼязку зі світоглядами '
            'з праці "Тотем і табу".'
        ),
    },
    {
        'name': 'Конрад Лоренц',
        'description': (
            'Етолог і мислитель, повʼязаний з еволюційним підходом до пізнання та апріорними '
            'структурами поведінки.'
        ),
    },
    {
        'name': 'Вернер Гейзенберг',
        'description': (
            'Фізик, один із творців квантової механіки; важливий для теми принципу '
            'невизначеності та меж спостереження.'
        ),
    },
    {
        'name': 'Курт Гедель',
        'description': (
            'Логік і математик; важливий для обговорення неповноти формальних систем '
            'та меж формального доведення.'
        ),
    },
    {
        'name': 'Джордж Поя',
        'description': (
            'Математик і автор праць про евристику; важливий для обговорення пошуку рішень '
            'і правдоподібного міркування.'
        ),
    },
    {
        'name': 'Альфред Реньї',
        'description': (
            'Математик, імовірнісник і популяризатор діалогічної форми в математичному '
            'мисленні.'
        ),
    },
    {
        'name': 'Станислав Лем',
        'description': (
            'Письменник і мислитель, автор "Соляриса"; центральна фігура для метафори океану '
            'та порівняння з LLM.'
        ),
    },
    {
        'name': 'LLM-агент',
        'description': (
            'Узагальнена роль штучного співрозмовника, який розглядає проблему '
            'у заданому контексті, теорії, епосі або стилі мислення.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed Solaris baseline sections and interlocutors from the project specification.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-interlocutors',
            action='store_true',
            help='Create or update sections only.',
        )

    def handle(self, *args, **options):
        section_created = 0
        section_updated = 0
        for payload in SECTIONS:
            _, created = Section.objects.update_or_create(
                slug=payload['slug'],
                defaults={
                    'name': payload['name'],
                    'brief': payload['brief'],
                    'order': payload['order'],
                },
            )
            if created:
                section_created += 1
            else:
                section_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Sections seeded: {section_created} created, {section_updated} updated.'
            )
        )

        if options['skip_interlocutors']:
            return

        interlocutor_created = 0
        interlocutor_updated = 0
        for payload in INTERLOCUTORS:
            _, created = Interlocutor.objects.update_or_create(
                name=payload['name'],
                defaults={'description': payload['description']},
            )
            if created:
                interlocutor_created += 1
            else:
                interlocutor_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Interlocutors seeded: '
                f'{interlocutor_created} created, {interlocutor_updated} updated.'
            )
        )
        self.stdout.write(
            'Spec items not seeded yet: section literature, section emblems, '
            'and separate personality-conversation menus need dedicated models first.'
        )
