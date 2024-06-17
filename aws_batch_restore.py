import argparse
import concurrent
import time
from datetime import datetime, timezone

import boto3


def time_ago(time=False):
    now = datetime.now(timezone.utc)
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        raise ValueError("invalid date %s of type %s" % (time, type(time)))
    second_diff = diff.seconds
    day_diff = diff.days
    if day_diff < 0:
        return ""
    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(round(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(round(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(round(day_diff)) + " days ago"
    if day_diff < 31:
        return str(round(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(round(day_diff / 30)) + " months ago"
    return str(round(day_diff / 365)) + " years ago"


def restore_all(pages, bucket):
    # iter over the pages from the paginator
    with concurrent.futures.ThreadPoolExecutor(10) as executor:
        for page in pages:
            # Find if there are any delete markers
            if "DeleteMarkers" in page.keys():
                for marker in page["DeleteMarkers"]:
                    print(f"\n📄 {marker['Key']}")
                    if (
                        marker["IsLatest"] is True
                        and marker["LastModified"] > deleted_after
                    ):
                        print(f"  This was deleted {time_ago(marker['LastModified'])}")
                        executor.submit(restore(marker, bucket))


def restore(delete_marker, bucket):
    global restore_count
    if prompt == "y" or prompt == "Y":
        answer = (
            input(f"  Would you like to restore {delete_marker['Key']}? [y/N] ") or "N"
        )
        if answer == "y" or answer == "Y":
            print("    🌱 Restoring...")
            file_object_version = s3.ObjectVersion(
                bucket, delete_marker["Key"], delete_marker["VersionId"]
            )
            file_object_version.delete()
            restore_count += 1
        else:
            print("    👟 Skipping...")
    else:
        print("    🌱 Restoring...")
        file_object_version = s3.ObjectVersion(
            bucket, delete_marker["Key"], delete_marker["VersionId"]
        )
        file_object_version.delete()
        restore_count += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore S3 objects from a bucket and prefix, it will delete the deletemarker and restore the latest version."
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="The name of the bucket to restore",
        action="store",
    )
    parser.add_argument(
        "--prefix",
        required=False,
        help="The prefix of the objects to restore",
        default="",
        action="store",
    )
    parser.add_argument(
        "--prompt",
        required=False,
        help="Whether to prompt before restoring, options y[Y],n[N]",
        default="y",
        action="store",
    )

    parser.add_argument(
        "--deleted-after",
        required=False,
        help="The time after which objects were deleted, defaults to 22 Oct 2019 20:00:00 UTC",
        default="2019-10-22T20:00:00Z",
        action="store",
    )
    start = time.time()
    args = parser.parse_args()
    params = vars(args)
    prompt = params["prompt"]
    s3client = boto3.client("s3")
    s3 = boto3.resource("s3")
    paginator = s3client.get_paginator("list_object_versions")
    operation_parameters = {"Bucket": params["bucket"], "Prefix": params["prefix"]}
    page_iterator = paginator.paginate(**operation_parameters)
    deleted_after = datetime.strptime(
        params["deleted_after"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    print(
        f"Restoring files deleted from {time_ago(False)} in 🪣 {params['bucket']}/{params['prefix']}"
    )
    restore_count = 0
    restore_all(page_iterator, params["bucket"])
    print(
        f" �� Restored {restore_count} objects in {round(time.time() - start, 2)} seconds"
    )
