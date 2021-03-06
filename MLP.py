from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import sys

from textwrap import wrap
import re
import itertools
import matplotlib
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
import scikitplot as skplt
import matplotlib.pyplot as plt

import numpy as np
import tensorflow as tf
import platform

log_dir = os.getcwd()
generic_slash = None
if platform.system() == 'Windows':
  generic_slash = '\\'
else:
  generic_slash = '/'

# set constants
TOTAL_EPOCHS = 10
learning_rate = 0.004   # The optimization initial learning rate
batch_size = 100
total_train_data = None
total_test_data = None

# network parameters
label_count = 10
n_hidden_1 = 256 # 1st layer number of features
n_hidden_2 = 256 # 2nd layer number of features
data_width = 28
data_height = 28

def encodeLabels(labels_decoded):
    encoded_labels = np.zeros(shape=(len(labels_decoded), label_count), dtype=np.int8)
    for x in range(0, len(labels_decoded)):
        some_label = labels_decoded[x]

        if 0 == some_label:
            encoded_labels[x][0] = 1
        elif 1 == some_label:
            encoded_labels[x][1] = 1
        elif 2 == some_label:
            encoded_labels[x][2] = 1
        elif 3 == some_label:
            encoded_labels[x][3] = 1
        elif 4 == some_label:
            encoded_labels[x][4] = 1
        elif 5 == some_label:
            encoded_labels[x][5] = 1
        elif 6 == some_label:
            encoded_labels[x][6] = 1
        elif 7 == some_label:
            encoded_labels[x][7] = 1
        elif 8 == some_label:
            encoded_labels[x][8] = 1
        elif 9 == some_label:
            encoded_labels[x][9] = 1
    return encoded_labels

def weight_variable(shape, std_dev):
  # Uses custom std. deviation as the reciprocal of the square root of the number of features
  # This initializes the weights with normal distribution that have a low std. deviation
  initial = tf.random_normal(shape, std_dev)
  return tf.Variable(initial)

def bias_variable(shape):
  # Uses default bias
  initial = tf.random_normal(shape)
  return tf.Variable(initial)

def multilayer_perceptron(x):
  x_image = tf.reshape(x, [-1, data_width*data_height])

  # Define Regularizer
  regularizer = tf.keras.constraints.MaxNorm(max_value=2)

  weights = {
    'h1': weight_variable([data_width*data_height, n_hidden_1], 1/tf.sqrt(float(data_width*data_height))),    #784x256
    'h2': weight_variable([n_hidden_1, n_hidden_2], 1/tf.sqrt(float(n_hidden_1))),                            #256x256
    'out': weight_variable([n_hidden_2, label_count], 1/tf.sqrt(float(n_hidden_2)))                           #256x10
  }
  biases = {
    'b1': bias_variable([n_hidden_1]),             #256x1
    'b2': bias_variable([n_hidden_2]),             #256x1
    'out': bias_variable([label_count])            #10x1
  }

  # Hidden layer 1 with RELU activation
  layer_1 = tf.add(tf.matmul(x_image, regularizer.__call__(w=weights['h1'])), biases['b1'])
  layer_1 = tf.nn.relu(layer_1)

  # Hidden layer with RELU activation     
  layer_2 = tf.add(tf.matmul(layer_1, regularizer.__call__(w=weights['h2'])), biases['b2'])
  layer_2 = tf.nn.relu(layer_2)

  # Batch Norm
  batch_norm = tf.layers.batch_normalization(layer_2,momentum=0.1,epsilon=1e-5)

  # Dropout
  keep_prob = tf.placeholder(tf.float32, name = "keep_prob")
  layer_2_drop = tf.nn.dropout(batch_norm, keep_prob)

  # Output layer with linear activation    
  out_layer = tf.nn.softmax(tf.matmul(layer_2_drop, weights['out']) + biases['out'], name = "ann")
  return out_layer, keep_prob

# Create a method to run the model, save it, & get statistics
def run_model():
  # Load training and eval data
  print("Data Loading")
  mnist = tf.keras.datasets.mnist
  (train_x, train_y),(test_x, test_y) = mnist.load_data()
  train_x, test_x = train_x / 255.0, test_x / 255.0

  total_train_data = len(train_y)
  total_test_data = len(test_y)

  print("Encoding Labels")
  # One-Hot encode the labels
  train_y = encodeLabels(train_y)
  test_y = encodeLabels(test_y)

  print("Size of:")
  print("- Training-set:\t\t{}".format(total_train_data))
  print("- Validation-set:\t{}".format(total_test_data))

  print("Creating Datasets")
  # Create the DATASETs
  train_x_dataset = tf.data.Dataset.from_tensor_slices(train_x)
  train_y_dataset = tf.data.Dataset.from_tensor_slices(train_y)
  test_x_dataset = tf.data.Dataset.from_tensor_slices(test_x)
  test_y_dataset = tf.data.Dataset.from_tensor_slices(test_y)

  print("Zipping The Data Together")
  # Zip the data and batch it and (shuffle)
  train_data = tf.data.Dataset.zip((train_x_dataset, train_y_dataset)).shuffle(buffer_size=total_train_data).repeat().batch(batch_size).prefetch(buffer_size=5)
  test_data = tf.data.Dataset.zip((test_x_dataset, test_y_dataset)).shuffle(buffer_size=total_test_data).repeat().batch(batch_size).prefetch(buffer_size=1)

  print("Creating Iterators")
  # Create Iterators
  train_iterator = train_data.make_initializable_iterator()
  test_iterator = test_data.make_initializable_iterator()

  # Create iterator operation
  train_next_element = train_iterator.get_next()
  test_next_element = test_iterator.get_next()

  print("Defining Model Placeholders")
  # Create the data & label placeholders
  x = tf.placeholder(tf.float32, [None, data_width, data_height], name = "x")
  y_ = tf.placeholder(tf.int8, [None, label_count], name = "y_")

  # Build the graph for the ANN
  ann, keep_prob = multilayer_perceptron(x)

  # Create loss (cross-entropy) op
  loss = tf.reduce_mean(
      tf.nn.softmax_cross_entropy_with_logits_v2(labels=y_, logits=ann))
  tf.summary.scalar('loss', loss)

  # Create train (adam-optimizer) op
  train = tf.train.AdamOptimizer(learning_rate, name='adam_op').minimize(loss)

  pred_label = tf.argmax(ann, 1, name='pred_label')
  actual_label = tf.argmax(y_, 1, name='actual_label')
  correct_prediction = tf.equal(pred_label, actual_label, name='correct_prediction')

  # Create accuracy op
  accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
  tf.summary.scalar('accuracy', accuracy)

  # Initialize and Run
  with tf.Session() as sess:
    merged = tf.summary.merge_all()
    train_writer = tf.summary.FileWriter(log_dir + generic_slash + 'tensorflow' + generic_slash + 'train', sess.graph)
    test_writer = tf.summary.FileWriter(log_dir + generic_slash + 'tensorflow' + generic_slash + 'test')
    sess.run(tf.global_variables_initializer())
    sess.run(train_iterator.initializer)
    sess.run(test_iterator.initializer)
    saver = tf.train.Saver()
    print("----------------------|----\---|-----|----/----\---|-----|---|\----|---------------------")
    print("----------------------|    |---|     ----|     -------|------|-\---|---------------------")
    print("----------------------|   |----|-----|---|   ---------|------|--\--|---------------------")
    print("----------------------|    |---|     ----|     |------|------|---\-|---------------------")
    print("----------------------|----/---|-----|----\----/---|-----|---|----\|---------------------")
    global_counter = 0
    # Number of training iterations in each epoch
    num_tr_iter = int(total_train_data / batch_size)
    for epoch in range(TOTAL_EPOCHS):
      for iteration in range(num_tr_iter):
        batch = sess.run(train_next_element)
        summary, _ = sess.run([merged, train], feed_dict={x: batch[0], y_: batch[1], keep_prob: 0.5})
        train_writer.add_summary(summary, global_counter)
        train_writer.flush()
        global_counter += 1
    
      # Run validation after every epoch
      validation_batch = sess.run(test_next_element)
      summary, acc, cross_entropy = sess.run([merged, accuracy, loss], feed_dict={x: validation_batch[0], y_: validation_batch[1], keep_prob: 1.0})
      print('Epoch ' + str(epoch+1) + ', Test Accuracy ' + str(acc) + ', Loss ' + str(cross_entropy))
      # Save the model
      saver.save(sess, log_dir + generic_slash + "tensorflow" + generic_slash + "mnist_model.ckpt")
      # Save the summaries
      test_writer.add_summary(summary, global_counter)
      test_writer.flush()
    
    # Re-initialize
    test_data = tf.data.Dataset.zip((test_x_dataset, test_y_dataset)).shuffle(buffer_size=total_test_data).repeat().batch(total_test_data).prefetch(buffer_size=1)
    test_iterator = test_data.make_initializable_iterator()
    test_next_element = test_iterator.get_next()
    sess.run(test_iterator.initializer)

    # Evaluate over the entire test dataset
    validation_batch = sess.run(test_next_element)
    print("Creating Confusion Matrix")
    predict, correct, acc, cross_entropy = sess.run([pred_label, actual_label, accuracy, loss], feed_dict={
        x: validation_batch[0], y_: validation_batch[1], keep_prob: 1.0})
    print('Final Test Accuracy ' + str(acc) + ', Loss ' + str(cross_entropy))
    skplt.metrics.plot_confusion_matrix(correct, predict, normalize=True)
    plt.savefig(log_dir + generic_slash + "tensorflow" + generic_slash + "plot.png")
    print("FINISHED")

# RUN THE PROGRAM
run_model()
