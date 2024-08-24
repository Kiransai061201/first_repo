import json
import psycopg2
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse

# PostgreSQL connection string
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'kiran',
    'password': 'kiran0612',
    'dbname': 'testdb'
}

# Initialize PostgreSQL connection
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        dbname=DB_CONFIG['dbname']
    )
    return conn

class User:
    def __init__(self, id=None, name=None, age=None, gender=None, email=None, mobile=None, address=None):
        self.id = id
        self.name = name
        self.age = age
        self.gender = gender
        self.email = email
        self.mobile = mobile
        self.address = address

class RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, response, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def _parse_post_data(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        return json.loads(post_data)

    def do_POST(self):
        if self.path == '/users':
            self.create_user()
        elif self.path == '/users/bulk':
            self.create_users_bulk()
        else:
            self._send_response({'error': 'Not found'}, 404)

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        if parsed_path.path.startswith('/users/'):
            self.get_user(parsed_path.path.split('/')[-1])
        else:
            self._send_response({'error': 'Not found'}, 404)

    def do_PUT(self):
        parsed_path = urlparse.urlparse(self.path)
        if parsed_path.path.startswith('/users/'):
            self.update_user(parsed_path.path.split('/')[-1])
        else:
            self._send_response({'error': 'Not found'}, 404)

    def do_DELETE(self):
        parsed_path = urlparse.urlparse(self.path)
        if parsed_path.path.startswith('/users/'):
            self.delete_user(parsed_path.path.split('/')[-1])
        else:
            self._send_response({'error': 'Not found'}, 404)

    def create_user(self):
        data = self._parse_post_data()
        user = User(name=data['name'], age=data['age'], gender=data['gender'], email=data['email'], mobile=data['mobile'], address=data['address'])

        conn = get_db_connection()
        cur = conn.cursor()
        sql_statement = """
            INSERT INTO users (name, age, gender, email, mobile, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id"""
        cur.execute(sql_statement, (user.name, user.age, user.gender, user.email, user.mobile, user.address))
        user.id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        self._send_response(user.__dict__, 201)

    def create_users_bulk(self):
        data = self._parse_post_data()
        users = [User(**item) for item in data]

        conn = get_db_connection()
        cur = conn.cursor()
        sql_statement = """
            INSERT INTO users (name, age, gender, email, mobile, address)
            VALUES (%s, %s, %s, %s, %s, %s)"""

        try:
            for user in users:
                cur.execute(sql_statement, (user.name, user.age, user.gender, user.email, user.mobile, user.address))
            conn.commit()
        except Exception as e:
            conn.rollback()
            self._send_response({'error': str(e)}, 500)
            return
        finally:
            cur.close()
            conn.close()

        self._send_response([user.__dict__ for user in users], 201)

    def get_user(self, id):
        conn = get_db_connection()
        cur = conn.cursor()
        sql_statement = """
            SELECT id, name, age, gender, email, mobile, address
            FROM users WHERE id = %s"""
        cur.execute(sql_statement, (id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            user = User(id=row[0], name=row[1], age=row[2], gender=row[3], email=row[4], mobile=row[5], address=row[6])
            self._send_response(user.__dict__)
        else:
            self._send_response({'error': 'User not found'}, 404)

    def update_user(self, id):
        data = self._parse_post_data()
        user = User(name=data['name'], age=data['age'], gender=data['gender'], email=data['email'], mobile=data['mobile'], address=data['address'])

        conn = get_db_connection()
        cur = conn.cursor()
        sql_statement = """
            UPDATE users
            SET name = %s, age = %s, gender = %s, email = %s, mobile = %s, address = %s
            WHERE id = %s"""
        cur.execute(sql_statement, (user.name, user.age, user.gender, user.email, user.mobile, user.address, id))
        conn.commit()
        cur.close()
        conn.close()

        self._send_response({'id': id, **data}, 200)

    def delete_user(self, id):
        conn = get_db_connection()
        cur = conn.cursor()
        sql_statement = "DELETE FROM users WHERE id = %s"
        cur.execute(sql_statement, (id,))
        conn.commit()
        cur.close()
        conn.close()

        self._send_response({'message': 'User deleted'}, 200)

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
