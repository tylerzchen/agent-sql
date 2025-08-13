import os
from rds_client import RDSClient
from dotenv import load_dotenv

load_dotenv()

CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DB_NAME = os.getenv("DATABASE_NAME")

client = RDSClient(
    cluster_arn=CLUSTER_ARN,
    secret_arn=SECRET_ARN,
    db_name=DB_NAME,
    region="us-east-1"
)

# Used to populate a sample RDS instance with data for testing
def generate_data():
    query = """

    """
    print("Testing database connection...")
    test_result = client.test_connection()
    if not test_result[0]:
        print(f"Connection failed: {test_result[1]}")
        return

    print("Generating data...")
    result = client.execute_query(query)
    if result['success']:
        print("Data generated successfully")
    else:
        print(f"Failed to generate data: {result['error']}")

def main():
    generate_data()

if __name__ == "__main__":
    main()