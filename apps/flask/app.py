#!/usr/bin/env python3

import os
import redis
import pymysql
import pika
from flask import Flask,make_response,request,jsonify
from prometheus_client import Counter, generate_latest, REGISTRY

app = Flask(__name__)

# 读取环境变量
redis_host = os.getenv("REDIS_HOST", "redis-service")
redis_port = os.getenv("REDIS_PORT", "6379")
db_host = os.getenv("DB_HOST", "mysql-service")
db_port = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "root123")
db_name = os.getenv("DB_NAME", "myapp")

# 连接redis 
try:
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    r.ping()
    print(f"Connected to Redis at{redis_host}:{redis_port}")
except Exception as e:
    print(f"Failed to connect to Redis: {e}")
    r = None

REQUESTS = Counter('flask_http_requests_total', 'Total HTTP requests',['method', 'endpoint'])

# 初始化mysql表格
def init_db():
    try:
        conn = pymysql.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name,
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                create table if not exists visits(
                    id int auto_increment primary key,
                    ip varchar(255),
                    visited_at datetime default current_timestamp
                )
            """)
            cursor.execute("""
                create table if not exists users(
                    id int auto_increment primary key,
                    name varchar(255)
                )
            """)
        conn.commit()
        conn.close()
        print(f"Connected to MySQL at {db_host}")
    except Exception as e:
        print(f"Failed to connect to MySQL: {e}")


init_db()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", 5672)
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "admin123")

# 向rabbitmq发送消息
@app.route("/send")
def send_message():
    """向 RabbitMQ 发送一条消息"""
    # 增加/send埋点 
    REQUESTS.labels(method='GET', endpoint='/send').inc()
    message = request.args.get("msg", "Hello, from Flask!")

    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # 声明队列hello，如果不存在则创建
        channel.queue_declare(queue='hello', durable=True)

        # 发送消息
        channel.basic_publish(
            exchange='',
            routing_key='hello',
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)  # 使消息持久化
        )

        connection.close()
        return jsonify({"status": "success", "message": f"Sent message: {message}"}), 200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
    
# 首页
@app.route("/")
def home():
    REQUESTS.labels(method='GET', endpoint='/').inc()
    if r is None:
        return "Redis is not available", 500
    try:
        count = r.incr("visits")
        return f"Hello! You are visitor number {count}"
    except Exception as e:
        return f"Redis Error: {e}", 500


# DB测试
@app.route("/db")
def db_test():
    REQUESTS.labels(method='GET', endpoint='/').inc()
    try:
        conn = pymysql.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name,
        )
        with conn.cursor() as cursor:
            cursor.execute('insert into users (name) values ("test_user")')
            cursor.execute("select COUNT(*) from users")
            count = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return f"DB Test Success! Total users: {count}"
    except Exception as e:
        return f"DB Test Error: {e}", 500

@app.route("/metrics")
def metrics():
    response = make_response(generate_latest(REGISTRY), 200)
    response.mimetype = "text/plain; charset=utf-8"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
