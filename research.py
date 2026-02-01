#!/usr/bin/env python3
"""
UnlockEgypt Site Researcher - CLI Entry Point

A research-oriented tool that gathers comprehensive information about
Egyptian archaeological sites from multiple sources.

Usage:
    python research.py                          # Research all sites
    python research.py -t monuments             # Research only monuments
    python research.py -t museums -m 5          # Research first 5 museums
    python research.py -v                       # Verbose output
"""

import argparse
import logging
import os

from site_researcher import SiteResearcher, PageType


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="UnlockEgypt Site Researcher - Comprehensive archaeological site research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Research Approach:
  This tool treats each site as a research subject, gathering information
  from multiple sources:
  - egymonuments.gov.eg (primary source)
  - Wikipedia (EN + AR)
  - Google Maps (practical info)
  - Official sources (tickets, hours)

Page Types:
  archaeological-sites  Ancient archaeological sites
  monuments            Historical monuments
  museums              Museums across Egypt
  sunken-monuments     Underwater archaeological sites

Examples:
  python research.py                              # Research all sites
  python research.py -t monuments                 # Research only monuments
  python research.py -t museums -m 3              # Research first 3 museums
  python research.py -o my_research.json          # Custom output path
  python research.py -v                           # Verbose output
        """
    )

    parser.add_argument(
        "-t", "--type",
        action="append",
        dest="page_types",
        choices=PageType.ALL_TYPES,
        help="Page type(s) to research (can be specified multiple times)"
    )

    parser.add_argument(
        "-o", "--output",
        default=os.path.join(os.path.dirname(__file__), "researched_sites.json"),
        help="Output JSON file path (default: researched_sites.json)"
    )

    parser.add_argument(
        "-m", "--max-sites",
        type=int,
        default=None,
        help="Maximum number of sites to research per page type"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    setup_logging(args.verbose)

    print("=" * 70)
    print("UnlockEgypt Site Researcher v3.2")
    print("Research-Oriented Multi-Source Data Collection")
    print("=" * 70)
    print()

    # Determine which page types to research
    page_types = args.page_types if args.page_types else PageType.ALL_TYPES
    type_names = [PageType.get_display_name(t) for t in page_types]

    print(f"Page types: {', '.join(type_names)}")
    if args.max_sites:
        print(f"Max sites per type: {args.max_sites}")
    print()

    print("Research sources:")
    print("  - egymonuments.gov.eg (primary)")
    print("  - Wikipedia (EN + AR)")
    print("  - Google Maps (practical info)")
    print("  - Official sources (tickets, hours)")
    print()

    headless = not args.no_headless

    with SiteResearcher(headless=headless) as researcher:
        sites = researcher.research_all(
            page_types=page_types,
            max_sites=args.max_sites
        )

        # Export results
        researcher.export_to_json(args.output)

        # Print summary
        print()
        print("=" * 70)
        print("RESEARCH COMPLETE")
        print("=" * 70)
        print(f"\nTotal sites researched: {len(sites)}")

        for site in sites:
            print(f"\n{site.name}")
            print(f"  Governorate: {site.governorate or 'N/A'}")
            print(f"  Era: {site.era or 'N/A'}")
            print(f"  Type: {site.tourismType} / {site.placeType}")
            print(f"  Arabic phrases: {len(site.arabicPhrases)}")
            print(f"  Tips: {len(site.tips)}")
            if site.uniqueFacts:
                print(f"  Unique facts: {len(site.uniqueFacts)}")


if __name__ == "__main__":
    main()
