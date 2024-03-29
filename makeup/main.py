# -*- coding: utf-8 -*-

import tensorflow as tf
import numpy as np
import os
from imageio import imread, imsave
import cv2
import time
import glob

basedir = os.path.abspath(os.path.dirname(__file__))

batch_size = 1
img_size = 256


def preprocess(img):
    return (img / 255. - 0.5) * 2


def deprocess(img):
    return (img + 1) / 2


def gen_makeup(img_path, result_filename_path, make_up_id):
    no_makeup = cv2.resize(imread(img_path), (img_size, img_size))
    X_img = np.expand_dims(preprocess(no_makeup), 0)

    tf.reset_default_graph()
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())

    saver = tf.train.import_meta_graph(
        os.path.join(basedir, './model', 'model.meta'))
    saver.restore(sess, tf.train.latest_checkpoint(
        os.path.join(basedir, './model')))

    graph = tf.get_default_graph()
    X = graph.get_tensor_by_name('X:0')
    Y = graph.get_tensor_by_name('Y:0')
    Xs = graph.get_tensor_by_name('generator/xs:0')

    makeups = glob.glob(os.path.join(
        basedir, 'imgs', 'makeup', make_up_id + '.*'))

    makeup = cv2.resize(
        imread(makeups[0]), (img_size, img_size))
    Y_img = np.expand_dims(preprocess(makeup), 0)
    Xs_ = sess.run(Xs, feed_dict={X: X_img, Y: Y_img})
    Xs_ = deprocess(Xs_)

    res = Xs_[0]
    imsave(result_filename_path, res)
    print("\n Makeup done!\n")

    return {"Xs": Xs, "X_img": X_img, "sess": sess, "X": X, "Y": Y}


def gen_makeup_all(img_path, result_filename_prefix_path, pool):
    print("gen_makeup_all")
    if not pool:
        no_makeup = cv2.resize(imread(img_path), (img_size, img_size))
        X_img = np.expand_dims(preprocess(no_makeup), 0)

        tf.reset_default_graph()
        sess = tf.Session()
        sess.run(tf.global_variables_initializer())

        saver = tf.train.import_meta_graph(
            os.path.join(basedir, './model', 'model.meta'))
        saver.restore(sess, tf.train.latest_checkpoint(
            os.path.join(basedir, './model')))

        graph = tf.get_default_graph()
        X = graph.get_tensor_by_name('X:0')
        Y = graph.get_tensor_by_name('Y:0')
        Xs = graph.get_tensor_by_name('generator/xs:0')

        pool = {"Xs": Xs, "X_img": X_img, "sess": sess, "X": X, "Y": Y}

    makeups = glob.glob(os.path.join(
        basedir, 'imgs', 'makeup', '[0-9]*.*'))
    print("makeups", len(makeups), makeups)

    for i in range(len(makeups)):
        item = makeups[i]
        appfix = item.rsplit('/', 1)[1]
        result_path = result_filename_prefix_path + "__" + appfix
        if os.path.exists(result_path):
            continue

        makeup = cv2.resize(imread(item), (img_size, img_size))
        Y_img = np.expand_dims(preprocess(makeup), 0)
        Xs_ = pool["sess"].run(pool["Xs"], feed_dict={
                               pool["X"]: pool["X_img"], pool["Y"]: Y_img})
        Xs_ = deprocess(Xs_)

        imsave(result_path, Xs_[0])

    print("\n Makeup all done!\n")
