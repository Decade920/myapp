#!/usr/bin/env python3

import pika

RABBITMQ_HOST = "rabbitmq-service"
RABBITMQ_USER = "admin"
RABBITMQ_PASS = "admin123"

# Callback function to handle incoming messages 
def callback(ch, method, properties, body):
    print(f"[x] Received {body.decode()}")
    print("[x] Done")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue='hello', durable=True)
    channel.basic_consume(queue='hello', on_message_callback=callback, auto_ack=False)

    print("[*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == "__main__":
    main()