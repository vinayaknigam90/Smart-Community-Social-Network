import boto3
from pymongo import MongoClient
import datetime
import time, threading

client = MongoClient("mongodb://admin:admin@ds251845.mlab.com:51845/socialcommunity")
db = client['socialcommunity']
mod_messages = db.mod_messages
#create sqs client
sqs= boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/507614993775/mails-queue'

def read_from_queue():
    #Recieve msg from sqs queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    if 'Messages' in response:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        _message = {
                    'subject': message['MessageAttributes']['Subject']['StringValue'],
                    'msg': message['MessageAttributes']['Msg']['StringValue'],
                    'sender': message['MessageAttributes']['Sender']['StringValue'],
                    'community': message['MessageAttributes']['Community']['StringValue'],
                    'recipient': message['MessageAttributes']['Recipient']['StringValue'],
                    'timestamp': datetime.datetime.utcnow()
                }
        result = mod_messages.insert_one(_message)

        print 'Inserted into Database'

        #Deleating the recieved msg from sqs queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )

        print 'The message  is deleated from the Queue'
    else:
        print 'No message in Queue'
    
    print time.ctime()
    threading.Timer(5,read_from_queue).start()

read_from_queue()

