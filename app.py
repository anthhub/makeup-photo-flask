# encoding:utf-8
# !/usr/bin/env python
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, make_response, send_from_directory, abort
import time
import os
from strUtil import Pic_str
import base64
from PIL import Image
import imagehash
from makeup.main import gen_makeup, gen_makeup_all
from cartoon.main import gen_cartoon
from concurrent.futures import ThreadPoolExecutor
import glob
import cv2
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado import ioloop

import logging

img_size = 256

LOG = logging.getLogger(__name__)

max_body_size = 800000000


executor = ThreadPoolExecutor(max_workers=100)

base_url = "http://10.180.9.102:5000"


app = Flask(__name__)
UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

RESULT_FOLDER = 'result'
app.config['RESULT_FOLDER'] = RESULT_FOLDER
basedir = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'JPG', 'PNG', 'gif', 'GIF'])


# gen/up photo 图片裁剪, 得到方形图
def trans_square(img_path):
    img = cv2.imread(img_path)
    height = img.shape[0]
    width = img.shape[1]
    size = min(height, width)
    span = 0
    if width > size:
        span = round((width - size) / 2)
    cropped = img[0:size, (0+span):(size+span)]
    std = cv2.resize(cropped, (img_size, img_size))
    cv2.imwrite(img_path, std)


# 异步任务
def async_cartoon_task(img_path, result_filename_path):
    print("async_cartoon_task")
    if not os.path.exists(result_filename_path):
        gen_cartoon(img_path, result_filename_path, "0")


def async_makeup_task(img_path, result_filename_prefix_path, pool):
    print("async_makeup_task")
    gen_makeup_all(img_path, result_filename_prefix_path, pool)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.errorhandler(400)
def frontend_error(error):
    return jsonify({"status": 1200, "msg": "参数错误:" + str(error)}), 400


@app.errorhandler(500)
def inner_error(error):
    return jsonify({"status": 1300, "msg": "内部错误" + str(error)}), 500


@app.route('/')
def hello_world():
    return 'Hello, World!'


# 通过上传的图片 生成新图片
@app.route('/gen_photo', methods=['POST'], strict_slashes=False)
def api_gen():
    result_file_dir = os.path.join(basedir, app.config['RESULT_FOLDER'])
    upload_file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(result_file_dir):
        os.makedirs(result_file_dir)

    if not os.path.exists(upload_file_dir):
        os.makedirs(upload_file_dir)

    f = request.files['photo']
    target_id = request.form['target_id']
    skip_storage = request.form.get("skip_storage", "0")

    if not target_id == "0":
        makeups = glob.glob(os.path.join(basedir, "makeup",
                                         'imgs', 'makeup', target_id + '.*'))
        if len(makeups) == 0:
            return jsonify({"status": 1000, "msg": "缺失妆面图"}), 400

    if f and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        # ext = fname.rsplit('.', 1)[1]

        ext = "png"

        highfreq_factor = 1
        hash_size = 8
        img_size = hash_size * highfreq_factor

        tmp_img_path = os.path.join(upload_file_dir, fname)
        f.save(tmp_img_path)

        trans_square(tmp_img_path)

        hash1 = imagehash.phash(Image.open(
            tmp_img_path), hash_size=hash_size, highfreq_factor=highfreq_factor)

        hash = str(hash1) + "__" + target_id

        new_filename = hash + '.' + ext
        result_filename_path = os.path.join(result_file_dir, new_filename)
        result_filename_prefix_path = os.path.join(
            result_file_dir, str(hash1))

        if skip_storage == "0" and os.path.exists(result_filename_path):
            print("hit storage: " + result_filename_path)
            return jsonify({"status": 0, "msg": "上传成功", "url": base_url + '/result/' + new_filename})

        pool = None

        if target_id == "0":
            gen_cartoon(tmp_img_path, result_filename_path, target_id)
        else:
            pool = gen_makeup(tmp_img_path, result_filename_path, target_id)

        # 发布异步任务 生成其他模式图片
        executor.submit(async_cartoon_task, tmp_img_path,
                        result_filename_prefix_path + "__0." + ext)

        executor.submit(async_makeup_task, tmp_img_path,
                        result_filename_prefix_path, pool)

        return jsonify({"status": 0, "msg": "上传成功", "url": base_url + '/result/' + new_filename})

    else:
        return jsonify({"status": 1001, "msg": "图片格式错误"}), 400


# 上传文件
@app.route('/up_photo', methods=['POST'], strict_slashes=False)
def api_upload():
    f = request.files['photo']
    makeup_id = request.form['makeup_id']

    if f and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        ext = fname.rsplit('.', 1)[1]
        new_filename = makeup_id + '.' + ext
        path = os.path.join("makeup/imgs/makeup", new_filename)
        f.save(path)
        trans_square(path)
        return jsonify({"status": 0, "msg": "上传成功", "url": base_url + '/makeup/' + new_filename})

    else:
        return jsonify({"status": 1001, "msg": "图片格式错误"}), 400


# makeup photo
@app.route('/makeup/<string:filename>', methods=['GET'])
def makeup_photo(filename):
    upload_file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
    if request.method == 'GET':
        if filename is None:
            pass
        else:
            image_data = open(os.path.join("makeup/imgs/makeup", '%s' %
                                           filename), "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
            return response
    else:
        pass


# result photo
@app.route('/result/<string:filename>', methods=['GET'])
def result_photo(filename):
    upload_file_dir = os.path.join(basedir, app.config['RESULT_FOLDER'])
    if request.method == 'GET':
        if filename is None:
            pass
        else:
            image_data = open(os.path.join(upload_file_dir, '%s' %
                                           filename), "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
            return response
    else:
        pass


@app.route('/download/<string:filename>', methods=['GET'])
def download(filename):
    if request.method == "GET":
        if os.path.isfile(os.path.join('upload', filename)):
            return send_from_directory('upload', filename, as_attachment=True)
        pass


# app.run(host="0.0.0.0", port=5000)

# if __name__ == '__main__':
#     app.run(host="0.0.0.0",port=8090)
port = 5000
bind = "0.0.0.0"

http_server = HTTPServer(WSGIContainer(app), max_body_size=max_body_size)
http_server.listen(port, address=bind)
LOG.info('Listening on http://{}:{}'.format(bind, port))
print('Listening on http://{}:{}'.format(bind, port))

ioloop.IOLoop.instance().start()
