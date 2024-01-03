from flask import Flask

restfulserver = Flask(__name__)

@restfulserver.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    restfulserver.run()