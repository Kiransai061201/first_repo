import boto3
from datetime import datetime, time, timezone
import pytz
def list_dynamodb_tables(dynamodb_client):
    dynamodb_tables = []
    response = dynamodb_client.list_tables()
    for table_name in response['TableNames']:
        table_description = dynamodb_client.describe_table(TableName=table_name)
        table_arn = table_description['Table']['TableArn']
        dynamodb_tables.append({'TableName': table_name, 'TableArn': table_arn})
    return dynamodb_tables
def export_dynamodb_table_backup(table_name, table_arn, s3_bucket_name, s3_prefix, dynamodb_client):
    try:
        response = dynamodb_client.create_backup(
            TableName=table_name,
            BackupName=f"{table_name}-backup"
        )
        while True:
            #########Check backup status and then we export to s3 bucket########
            backup_status = dynamodb_client.describe_backup(
                BackupArn=response['BackupDetails']['BackupArn']
            )['BackupDescription']['BackupDetails']['BackupStatus']
            if backup_status == 'AVAILABLE':
                break
            print(f"Backup status: {backup_status}. Waiting for backup to complete...")
            time.sleep(5)
        #########to keep the arn together you can keep it as is if you want to, because s3 considers '/' as paths are considered ########
        # #date_format = datetime.now(tz=pytz.utc)
        # date_format='%m/%d/%Y %H:%M:%S %Z'
        date = datetime.now(tz=pytz.utc)
        # print('Current date & time is:', date.strftime(date_format))
        # date = date.astimezone(timezone(pytz.timezone('America/Los_Angeles')))
        # print(date)
        # print('Local date & time is  :', date.strftime(date_format))
        # print(datetime.now())
        response = dynamodb_client.export_table_to_point_in_time(
            TableArn=table_arn,
            ExportTime=date,
            S3Bucket=s3_bucket_name,
            S3Prefix=f"{s3_prefix}/{table_arn}",
            S3SseAlgorithm='AES256',
            ExportFormat='DYNAMODB_JSON'
        )
        print(f"Exported backup of table '{table_name}' to S3 bucket '{s3_bucket_name}'")
    except Exception as e:
        print(f"Error exporting backup of table '{table_name}': {e}")
def export_all_dynamodb_table_backups(s3_bucket_name, dynamodb_client):
    tables = list_dynamodb_tables(dynamodb_client)
    s3_prefix = 'dynamodb-backups'
    for table in tables:
        table_name = table['TableName']
        table_arn = table['TableArn']
        export_dynamodb_table_backup(table_name, table_arn, s3_bucket_name, s3_prefix, dynamodb_client)