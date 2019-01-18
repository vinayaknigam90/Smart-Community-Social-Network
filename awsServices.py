import boto3
def sendEmail(message, subject):
    client = boto3.client('ses')
    response = client.send_email(
        Destination={
            'BccAddresses': [
            ],
            'CcAddresses': [
            ],
            'ToAddresses': [
                'socialnetwork281@gmail.com',
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': message, 
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': 'This is the message body in text format.',
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': subject,
            },
        },
        Source='akhilesh.deowanshi@gmail.com',
    )


def sendMessage(userContact,userName,communityName):
    client = boto3.client('sns')
    number = '+15105857576'
    client.publish(PhoneNumber = number, Message='New community has been crerated by ' + userName + '. please approve by login on console.' )

def sendDeclineMessage(userContact,message):
    client = boto3.client('sns')
    userContact = '+1' +userContact
    client.publish(PhoneNumber = userContact, Message=message )
