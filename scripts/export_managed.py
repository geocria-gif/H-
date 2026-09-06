"""Trigger a Firestore managed export to Cloud Storage (server-side).

The export runs on Google's side: it reads ZERO rows from the daily app quota.
Requirements:
    - the service account needs roles/datastore.importExportAdmin + storage
      write access on the target bucket;
    - ``--uri gs://bucket/backups`` (a timestamped sub-folder is appended).

Usage:
    py -3.14 scripts/export_managed.py --uri gs://meu-bucket/backups \\
        --service-account gestoper-...json
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    parser = argparse.ArgumentParser(description="Firestore managed export")
    parser.add_argument('--uri', required=True,
                        help="gs://<bucket>/<path> prefix")
    parser.add_argument('--service-account', default=None,
                        help="path to service account json (default env/file)")
    args = parser.parse_args()

    from app.firebase_db import trigger_managed_export
    operation = trigger_managed_export(args.uri, sa_path=args.service_account)
    name = operation.get('name', '')
    print(f"operacao iniciada: {name}")
    print("acompanhe pelo bucket GCS ou:")
    print(f"  GET https://firestore.googleapis.com/v1/{name}")


if __name__ == '__main__':
    main()