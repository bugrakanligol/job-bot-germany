#!/usr/bin/env python3
"""
Job Bot Germany — CLI entrypoint

Commands:
  parse-cv          Parse CV PDF and cache the profile
  scrape            Scrape job listings from all sources
  score             Score all unscored jobs against the CV
  run               scrape + score in one step
  list              List jobs in the database
  cover-letter <id> Generate a cover letter for a job ID
  stats             Show database statistics
"""
import argparse
import logging
import sys

from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("job-bot")


def cmd_parse_cv(args) -> None:
    from src.cv_parser import parse_cv

    profile = parse_cv()
    print(f"CV parsed for: {profile.get('name', 'Unknown')}")
    print(f"Skills: {', '.join(profile.get('skills', [])[:8])}")


def cmd_scrape(args) -> None:
    from src.scraper import scrape_all

    sources = args.sources.split(",") if args.sources else None
    result = scrape_all(sources=sources)
    print(
        f"Scraping done: {result['saved']} new jobs saved, "
        f"{result['skipped']} duplicates skipped "
        f"(total fetched: {result['total']})."
    )


def cmd_score(args) -> None:
    from src.matcher import score_all_unscored

    scored = score_all_unscored(use_batch=getattr(args, "batch", False))
    print(f"Scored {scored} jobs.")


def cmd_run(args) -> None:
    cmd_scrape(args)
    cmd_score(args)


def cmd_list(args) -> None:
    from src import database

    database.init_db()
    status_filter = args.status
    if status_filter:
        jobs = database.get_jobs_by_status(status_filter)
    else:
        jobs = database.get_all_jobs()

    if not jobs:
        print("No jobs found.")
        return

    rows = []
    for j in jobs:
        score_str = str(j["score"]) if j["score"] is not None else "-"
        rows.append([
            j["id"],
            (j["title"] or "")[:45],
            (j["company"] or "")[:25],
            (j["location"] or "")[:20],
            j["source"],
            score_str,
            j["status"],
        ])

    headers = ["ID", "Title", "Company", "Location", "Source", "Score", "Status"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))
    print(f"\nTotal: {len(jobs)} job(s)")


def cmd_cover_letter(args) -> None:
    from src.cover_letter import generate_and_save

    job_id = args.job_id
    letter = generate_and_save(job_id)
    print(f"\n{'='*60}")
    print(f"Cover Letter — Job ID {job_id}")
    print('='*60)
    print(letter)
    print('='*60)


def cmd_stats(args) -> None:
    from src import database

    database.init_db()
    stats = database.get_stats()
    print(f"Total jobs:    {stats['total_jobs']}")
    print(f"CV profiles:   {stats['cv_profiles']}")
    print()

    if stats["by_status"]:
        rows = [[s, c] for s, c in sorted(stats["by_status"].items())]
        print("By status:")
        print(tabulate(rows, headers=["Status", "Count"], tablefmt="simple"))

    if stats["by_source"]:
        print()
        rows = [[s, c] for s, c in sorted(stats["by_source"].items())]
        print("By source:")
        print(tabulate(rows, headers=["Source", "Count"], tablefmt="simple"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-bot",
        description="Automated German job search assistant",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("parse-cv", help="Parse the CV PDF and cache the profile")

    scrape_p = sub.add_parser("scrape", help="Scrape job listings")
    scrape_p.add_argument(
        "--sources",
        metavar="SRC",
        help="Comma-separated list of sources: bundesagentur,indeed,stepstone",
    )

    score_p = sub.add_parser("score", help="Score all unscored jobs against the CV")
    score_p.add_argument(
        "--batch",
        action="store_true",
        help="Use Batch API (async, 50%% cheaper) instead of synchronous calls",
    )

    run_p = sub.add_parser("run", help="Scrape + score in one step")
    run_p.add_argument(
        "--sources",
        metavar="SRC",
        help="Comma-separated list of sources",
    )
    run_p.add_argument(
        "--batch",
        action="store_true",
        help="Use Batch API for scoring (async, 50%% cheaper)",
    )

    list_p = sub.add_parser("list", help="List jobs in the database")
    list_p.add_argument(
        "--status",
        metavar="STATUS",
        help="Filter by status: new, shortlisted, reviewed, skipped",
    )

    cl_p = sub.add_parser("cover-letter", help="Generate a cover letter for a job")
    cl_p.add_argument("job_id", type=int, metavar="JOB_ID")

    sub.add_parser("stats", help="Show database statistics")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "parse-cv": cmd_parse_cv,
        "scrape": cmd_scrape,
        "score": cmd_score,
        "run": cmd_run,
        "list": cmd_list,
        "cover-letter": cmd_cover_letter,
        "stats": cmd_stats,
    }

    if args.command not in handlers:
        parser.print_help()
        sys.exit(1)

    try:
        handlers[args.command](args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    except Exception as e:
        logger.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
