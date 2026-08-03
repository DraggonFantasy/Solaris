from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from dialogues.gemini_illustrations import (
    import_gemini_illustrations,
    is_gemini_share_url,
)
from dialogues.models import AuditLog, Dialogue


class Command(BaseCommand):
    help = (
        "Import missing illustrations and explicit recommended literature for "
        "published dialogues backed by public Gemini share links."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List eligible dialogues without downloading or saving images.",
        )
        parser.add_argument(
            "--dialogue-id",
            action="append",
            type=int,
            dest="dialogue_ids",
            help="Restrict processing to a dialogue ID. May be supplied repeatedly.",
        )
        parser.add_argument(
            "--include-existing",
            action="store_true",
            help=(
                "Also revisit dialogues that already have illustrations and "
                "literature. Existing Gemini imports are skipped idempotently."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Process at most this many eligible dialogues.",
        )

    def _eligible_dialogues(self, options):
        queryset = Dialogue.objects.filter(
            status=Dialogue.STATUS_PUBLISHED,
        ).exclude(source_url="")
        if options["dialogue_ids"]:
            queryset = queryset.filter(pk__in=options["dialogue_ids"])
        if not options["include_existing"]:
            queryset = queryset.filter(
                Q(illustrations__isnull=True) | Q(recommended_literature="")
            ).distinct()

        limit = options["limit"]
        dialogues = []
        for dialogue in queryset.order_by("pk").iterator():
            if not is_gemini_share_url(dialogue.source_url):
                continue
            dialogues.append(dialogue)
            if limit is not None and len(dialogues) >= limit:
                break
        return dialogues

    def handle(self, *args, **options):
        if options["limit"] is not None and options["limit"] <= 0:
            raise CommandError("--limit must be greater than zero.")

        dialogues = self._eligible_dialogues(options)
        if not dialogues:
            self.stdout.write("No eligible published Gemini dialogues found.")
            return

        self.stdout.write(f"Eligible dialogues: {len(dialogues)}")
        if options["dry_run"]:
            for dialogue in dialogues:
                self.stdout.write(
                    f"[{dialogue.pk}] {dialogue.title} — {dialogue.source_url}"
                )
            self.stdout.write(
                self.style.WARNING(
                    "Dry run: no illustrations or literature were imported."
                )
            )
            return

        imported = 0
        literature_imported = 0
        duplicates = 0
        asset_failures = 0
        dialogue_failures = 0
        for dialogue in dialogues:
            try:
                result = import_gemini_illustrations(dialogue)
            except Exception as exc:
                dialogue_failures += 1
                AuditLog.objects.create(
                    user=None,
                    action="backfill_gemini_illustrations_failed",
                    object_type="Dialogue",
                    object_id=str(dialogue.pk),
                    details=str(exc)[:1000],
                )
                self.stderr.write(
                    self.style.ERROR(
                        f"[{dialogue.pk}] {dialogue.title}: failed: {exc}"
                    )
                )
                continue

            imported += result.imported
            literature_imported += int(result.literature_imported)
            duplicates += result.skipped_duplicates
            asset_failures += result.failed
            action = (
                "backfill_gemini_illustrations_failed"
                if (
                    result.failed
                    and not result.imported
                    and not result.literature_imported
                )
                else "backfill_gemini_illustrations"
            )
            AuditLog.objects.create(
                user=None,
                action=action,
                object_type="Dialogue",
                object_id=str(dialogue.pk),
                details=(
                    f"Found: {result.found}; imported: {result.imported}; "
                    f"duplicates: {result.skipped_duplicates}; failed: {result.failed}; "
                    f"literature found: {result.literature_found}; "
                    f"literature imported: {result.literature_imported}"
                ),
            )
            self.stdout.write(
                f"[{dialogue.pk}] {dialogue.title}: found={result.found}, "
                f"imported={result.imported}, "
                f"duplicates={result.skipped_duplicates}, failed={result.failed}, "
                f"literature_found={result.literature_found}, "
                f"literature_imported={result.literature_imported}"
            )

        summary = (
            f"Processed: {len(dialogues)}; imported images: {imported}; "
            f"imported literature: {literature_imported}; "
            f"duplicates: {duplicates}; asset failures: {asset_failures}; "
            f"dialogue failures: {dialogue_failures}."
        )
        if dialogue_failures or asset_failures:
            self.stderr.write(self.style.ERROR(summary))
            raise CommandError("Gemini illustration backfill completed with errors.")
        self.stdout.write(self.style.SUCCESS(summary))
