# from flask import Flask
# from markupsafe import escape
#
# app = Flask(__name__)
#
# # @app.route("/")
# # def hello_world():
# #     return "<p>Hello, World!</p>"
#
# @app.route('/')
# def index():
#     return 'Index Page'
# #
# # @app.route('/hello')
# # def hello():
# #     return 'Hello, World'
#
# @app.route('/user/<username>')
# def show_user_profile(username):
#     # show the user profile for that user
#     return f'User {escape(username)}'
#
# @app.route('/post/<int:post_id>')
# def show_post(post_id):
#     # show the post with the given id, the id is an integer
#     return f'Post {post_id}'
#
# @app.route('/path/<path:subpath>')
# def show_subpath(subpath):
#     # show the subpath after /path/
#     return f'Subpath {escape(subpath)}'
#
#
# if __name__ == '__main__':
#     app.run()

from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        if name.lower() == 'kappa':
            return "OK"
        else:
            return "Error: Falscher Name", 400

    # Einfaches HTML-Formular für die GET-Anfrage
    return '''
        <form method="post">
            Name: <input type="text" name="name"><br>
            <input type="submit" value="Submit">
        </form>
    '''

if __name__ == '__main__':
    app.run(debug=True)
