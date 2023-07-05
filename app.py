import random
import sqlite3
import time

from flask import Flask, render_template, request, url_for, flash, redirect, send_file, make_response
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from os import listdir
from os.path import isfile, join
import shutil
import spec_parser
import spec_parser_t2
import csv
import os
import traceback
from multiprocessing import Manager, Process
import json
from flask_session import Session
from flask import Flask, render_template, redirect, request, session

header = ['Document Name', 'Search Word Text', 'Secondary Search', 'Element Identifier ', 'Element Text']
if not os.path.exists("session_files"):
    os.mkdir("session_files")
import re

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config['SECRET_KEY'] = '4321 some random very scrt key 1234'

# Creating the upload folder
upload_folder = "uploads/"
if not os.path.exists(upload_folder):
    os.mkdir(upload_folder)

# Configuring the upload folder
app.config['UPLOAD_FOLDER'] = upload_folder

# configuring the allowed extensions
allowed_extensions = ['pdf', 'csv']


def read_csv(csv_inputs, separator=','):
    """
  reading csv file from file system to python list of lists
  :param csv_inputs:
  :return:
  """
    try:
        with open(csv_inputs, newline='', encoding='cp1252') as f:
            reader = csv.reader(f, quotechar='"',
                                delimiter=separator,
                                quoting=csv.QUOTE_ALL,
                                skipinitialspace=True)
            # we should ignore the first line(header)
            data = list(reader)
            data = [[x[0].replace(';', ','), x[1].replace(';', '\n'), x[2], x[3], x[4]] for x in data]
        return data[1:]
    except Exception as e:
        print(str(e))
        print("File {} not found or format is wrong".format(csv_inputs))


def get_db_connection():
    """
    creates DB connection
    :return:
    """
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print("Exception in get_db_connection: {}".format(str(e)))
        print(traceback.format_exc())


def chunks(lst, n):
    """
    split the list into N equal-sized chunks
    :param lst:
    :param n:
    :return:
    """
    try:
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    except Exception as e:
        print("Exception in chunks: {}".format(str(e)))
        print(traceback.format_exc())


def get_single_filter_by_id(filter_id):
    """
    :param filter_id:
    :return:
    """
    try:
        conn = get_db_connection()
        filter = conn.execute('SELECT * FROM filters WHERE id = ?',
                              (filter_id,)).fetchone()
        conn.close()
        if filter is None:
            abort(404)
        return filter
    except Exception as e:
        print("Exception in get_single_filter_by_id: {}".format(str(e)))
        print(traceback.format_exc())


# Sending the file to the user
@app.route('/download', methods=['GET', 'POST'])
def download():
    """
    parse PDF's
    :return:
    """
    try:

        print('download')

        session_id = session.get("sess_id")
        session_path = os.path.join("session_files", session_id)
        if os.path.exists('results.zip'):
            os.remove('results.zip')
        print(session_id)
        if not os.path.exists(session_path):
            flash('Please select PDF files fist!')
            return redirect(url_for('index'))
        filtr_id =  request.form.get('filter_to_use')
        print(filtr_id)
        files = [join(session_path, f) for f in listdir(session_path) if
                 isfile(join(session_path, f)) and '.pdf' in f.lower()]
        if len(files) == 0:
            flash('Please select PDF files fist!')
            return redirect(url_for('index'))

        conn = get_db_connection()
        posts = conn.execute('SELECT * FROM filters WHERE id = {}'.format(filtr_id)).fetchall()
        flash("Filter selected!")
        filters = []
        for p in posts:
            filters.append([list(p)[2].split(','), list(p)[3].split('\n')])
        for f in filters:
            print(f)
        conn.close()

        with open('regex.json', 'r') as f:
            data = json.load(f)

        patterns = [x["regex"] for x in list(data.values())]
        data = {}
        for i in range(7):
            temp = []
            try:
                data[i + 1] = [filters[i][0],
                               filters[i][1], patterns[i]]
            except Exception:
                data[i + 1] = [''.split('\n'), ''.split('\n'), patterns[i]]

        data[8] = [[''], [''], '[a-z]+.']
        data[9] = [[''], [''], '[a-z]+.']
        request.form.get("name")
        if os.path.exists('results'):
            shutil.rmtree('results')
        os.mkdir('results')
        folder = 'results'
        csv_path = os.path.join(folder, 'result.csv')
        chunks_file = list(chunks(files, 16))
        print('+++++')
        print(request.form.get('type'))
        if request.form.get('type') == 'new':
            with Manager() as manager:
                L = manager.list()
                processes = []
                file_names = []
                for chunk in chunks_file:
                    for filename in chunk:
                        try:
                            print('DD')
                            print(data)
                            # method to call in multithread mode - prepare_to_parsing
                            # arguments of prepare_to_parsing - filename and folder
                            p = Process(target=spec_parser_t2.prepare_to_parsing, args=(filename, folder, L, data))
                            # start processes
                            file_names.append(os.path.join(folder,
                                                           os.path.basename(filename).lower().replace('.pdf',
                                                                                                      '.csv')))
                            p.start()
                            processes.append(p)
                        except Exception:
                            pass
                    for p in processes:
                        p.join()
                L = [x for x in L]
                L.sort(key=lambda x: x[0])
                L.insert(0, header)
                json_path = os.path.join(folder, 'result.json')
                result_json = []
                for x in L[1:]:
                    temp = {
                        "Specification Section Name": x[0],
                        "Specification Section Number": x[0].split()[0],
                        "Section Name": x[1],
                        "Item Type": x[2],
                        "SubSection Number": x[3],
                        "SubSection Text": x[4]
                    }
                    result_json.append(temp)
                file_names.append(json_path)
                with open(json_path, 'w') as f:
                    json.dump(result_json, f, indent=4)
                file_names.append(csv_path)
                with open(csv_path, "w",
                          newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(L)
                for chunk in chunks_file:
                    for filename in chunk:
                        os.remove(filename)
                shutil.make_archive('results', 'zip', 'results')
                shutil.rmtree('results')
        else:
            try:
                print('Parsed as an old type')
                with Manager() as manager:
                    L = manager.list()
                    processes = []
                    file_names = []
                    for chunk in chunks_file:
                        for filename in chunk:
                            try:
                                print('DD')
                                print(data)
                                # method to call in multithread mode - prepare_to_parsing
                                # arguments of prepare_to_parsing - filename and folder
                                p = Process(target=spec_parser.prepare_to_parsing, args=(filename, folder, L, data))
                                # start processes
                                file_names.append(os.path.join(folder,
                                                               os.path.basename(filename).lower().replace('.pdf',
                                                                                                          '.csv')))
                                p.start()
                                processes.append(p)
                            except Exception:
                                pass
                        for p in processes:
                            p.join()
                    L = [x for x in L]
                    L.sort(key=lambda x: x[0])
                    L.insert(0, header)
                    json_path = os.path.join(folder, 'result.json')
                    result_json = []
                    for x in L[1:]:
                        temp = {
                            "Specification Section Name": x[0],
                            "Specification Section Number": x[0].split()[0],
                            "Section Name": x[1],
                            "Item Type": x[2],
                            "SubSection Number": x[3],
                            "SubSection Text": x[4]
                        }
                        result_json.append(temp)
                    file_names.append(json_path)
                    with open(json_path, 'w') as f:
                        json.dump(result_json, f, indent=4)
                    file_names.append(csv_path)
                    with open(csv_path, "w",
                              newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(L)
                    for chunk in chunks_file:
                        for filename in chunk:
                            os.remove(filename)
                    shutil.make_archive('results', 'zip', 'results')
                    shutil.rmtree('results')

            except Exception as e:
                print(traceback.format_exc())
        if os.path.exists('results.zip'):
            flash("File result.zip downloaded. Please check. ")
            return send_file('results.zip', as_attachment=True)
        else:
            flash("Failed to create the result archive! Plase doublchck the file type.")
            return redirect(url_for('index'))
    except Exception as e:
        print("Exception in download: {}".format(str(e)))
        print(traceback.format_exc())
        flash("File result.zip downloaded. Please check. ")
        return redirect(url_for('index'))


@app.route('/')
def index():
    """
    main view
    :return:
    """
    try:
        conn = get_db_connection()
        posts = conn.execute('SELECT * FROM filters').fetchall()
        conn.close()
        print(posts)
        return render_template('index.html', posts=posts)
    except Exception as e:
        print("Exception in get_single_filter_by_id: {}".format(str(e)))
        print(traceback.format_exc())


@app.route('/<int:post_id>')
def post(post_id):
    """
    filter view
    :param post_id:
    :return:
    """
    try:
        post = get_single_filter_by_id(post_id)
        return render_template('post.html', post=post)
    except Exception as e:
        print("Exception in post: {}".format(str(e)))
        print(traceback.format_exc())


@app.route('/create', methods=('GET', 'POST'))
def create():
    """
    crates a new filter
    :return:
    """
    try:
        if request.method == 'POST':
            primary_filter = request.form['primary_filter']
            secondary_filter = request.form['secondary_filter']
            name = request.form['name']
            description = request.form['description']
            files = request.files.getlist('files')
            img_path = ''
            if files[0].filename:
                print(files)
                files[0].save(
                    os.path.join('static/css/images', secure_filename(files[0].filename)))
                img_path = os.path.join('static/css/images', secure_filename(files[0].filename))
            else:
                img_path = 'static/css/images/noimage.jpg'

            print(img_path)
            if not primary_filter:
                flash('primary_filter is required!')
            else:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO filters (primary_filter, secondary_filter, name, description, img_path) VALUES (?, ?, ?,?,?)',
                    (primary_filter, secondary_filter, name, description, img_path))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
        return render_template('create.html')
    except Exception as e:
        print("Exception in post: {}".format(str(e)))
        print(traceback.format_exc())


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    """
    edit filter
    :param id:
    :return:
    """
    try:
        post = get_single_filter_by_id(id)

        if request.method == 'POST':
            primary_filter = request.form['primary_filter']
            secondary_filter = request.form['secondary_filter']
            name = request.form['name']
            description = request.form['description']


            if not primary_filter:
                flash('primary_filter is required!')
            else:
                conn = get_db_connection()
                filter = conn.execute('SELECT * FROM filters WHERE id = ?',
                                      (str(id))).fetchone()
                img_path = filter['img_path']
                conn.execute(
                    'UPDATE filters SET primary_filter = ?, secondary_filter = ?, name = ?, description = ?, img_path = ?'
                    ' WHERE id = ?',
                    (primary_filter, secondary_filter, name, description, img_path, id))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))

        return render_template('edit.html', post=post)
    except Exception as e:
        print("Exception in post: {}".format(str(e)))
        print(traceback.format_exc())


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    """
    delete filter
    :param id:
    :return:
    """
    try:
        filter = get_single_filter_by_id(id)
        conn = get_db_connection()
        conn.execute('DELETE FROM filters WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('"{}" was successfully deleted!'.format(filter['primary_filter']))
        return redirect(url_for('index'))
    except Exception as e:
        print("Exception in delete: {}".format(str(e)))
        print(traceback.format_exc())


def check_file_extension(filename):
    """
    check if file extension is valid
    :param filename:
    :return:
    """
    return filename.split('.')[-1].lower() in allowed_extensions


@app.route('/upload', methods=['GET', 'POST'])
def uploadfile():
    print('uploadfile')
    print(request.files.getlist('files'))
    print([str(f) for f in request.files.getlist('files')])
    try:
        if [str(f) for f in request.files.getlist('files')] == ["<FileStorage: '' ('application/octet-stream')>"]:
            flash("Please upload files first")
            return redirect(url_for('index'))
    except Exception as e:
        flash(str(e))
        print('++++')
        return redirect(url_for('index'))

    try:
        if request.method == 'POST':  # check if the method is post
            files = request.files.getlist('files')  # get the file from the files object

            pdf_files = [join(app.config['UPLOAD_FOLDER'], f) for f in listdir(app.config['UPLOAD_FOLDER']) if
                         isfile(join(app.config['UPLOAD_FOLDER'], f))]

            session_id = str(random.randint(11111111, 99999999))
            session_path = os.path.join("session_files", session_id)
            if not os.path.exists(session_path):
                os.mkdir(session_path)
            for f in pdf_files:
                os.remove(f)
            uploaded = 0
            for f in files:
                print(f.filename)
                if check_file_extension(f.filename):
                    uploaded += 1
                    f.save(
                        os.path.join(session_path, secure_filename(f.filename)))  # this will secure the file

            session["sess_id"] = session_id
            flash("{} PDF files uploaded".format(uploaded))
            return redirect(url_for('index'))
            # return 'file uploaded successfully'  # Display thsi message after uploading
    except Exception as e:
        print("Exception in uploadfile: {}".format(str(e)))
        print(traceback.format_exc())


@app.route('/uploadcsv', methods=['GET', 'POST'])
def uploadfilecsv():
    print('uploadfilecsv')
    try:
        if [str(f) for f in request.files.getlist('files')] == ["<FileStorage: '' ('application/octet-stream')>"]:
            flash("Please upload files first")
            return redirect(url_for('index'))
    except Exception as e:
        flash(str(e))
        return redirect(url_for('index'))
    try:
        if request.method == 'POST':  # check if the method is post
            files = request.files.getlist('files')
            print(files)
            for f in files:
                print(f.filename)
                # Saving the file in the required destination
                if check_file_extension(f.filename):
                    f.save(
                        os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))

            data = read_csv(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            uploaded = 0
            for row in data:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO filters (primary_filter, secondary_filter, name, description, img_path) VALUES (?, ?,?, ?, ?)',
                    (row[0], row[1], row[2], row[3], row[4]))
                conn.commit()
                conn.close()
                uploaded += 1
            flash('{} new filters uploaded successfully'.format(str(uploaded)), 'info')
            return redirect(url_for('index'))

            # return redirect(url_for('index')) #'file uploaded successfully'  # Display thsi message after uploading
    except Exception as e:
        print("Exception in uploadfilecsv: {}".format(str(e)))
        print(traceback.format_exc())
