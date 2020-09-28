# recursive multi-step forecast with linear algorithms
from math import sqrt
from numpy import split
from numpy import array
from pandas import read_csv
from sklearn.metrics import mean_squared_error
from matplotlib import pyplot
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Lasso
from sklearn.linear_model import Ridge
from sklearn.linear_model import ElasticNet
from sklearn.linear_model import HuberRegressor
from sklearn.linear_model import Lars
from sklearn.linear_model import LassoLars
from sklearn.linear_model import PassiveAggressiveRegressor
from sklearn.linear_model import RANSACRegressor
from sklearn.linear_model import SGDRegressor

# 将数据按week分割成训练集和测试集
def split_dataset(data):
	# 分割成训练集和测试集
	train, test = data[1:-328], data[-328:-6]
	# 分割成以周为单位
	train = array(split(train, len(train)/7))
	test = array(split(test, len(test)/7))
	return train, test

# evaluate one or more weekly forecasts against expected values
def evaluate_forecasts(actual, predicted):
	scores = list()
	# calculate an RMSE score for each day
	for i in range(actual.shape[1]):
		# calculate mse
		mse = mean_squared_error(actual[:, i], predicted[:, i])
		# calculate rmse
		rmse = sqrt(mse)
		# store
		scores.append(rmse)
	# calculate overall RMSE
	s = 0
	for row in range(actual.shape[0]):
		for col in range(actual.shape[1]):
			s += (actual[row, col] - predicted[row, col])**2
	score = sqrt(s / (actual.shape[0] * actual.shape[1]))
	return score, scores

# summarize scores
def summarize_scores(name, score, scores):
	s_scores = ', '.join(['%.1f' % s for s in scores])
	print('%s: [%.3f] %s' % (name, score, s_scores))

# 创建模型列表
def get_models(models=dict()):
	models['lr'] = LinearRegression()
	models['lasso'] = Lasso()
	models['ridge'] = Ridge()
	models['en'] = ElasticNet()
	models['huber'] = HuberRegressor()
	models['lars'] = Lars()
	models['llars'] = LassoLars()
	models['pa'] = PassiveAggressiveRegressor(max_iter=1000, tol=1e-3)
	models['ranscac'] = RANSACRegressor()
	models['sgd'] = SGDRegressor(max_iter=1000, tol=1e-3)
	print('Defined %d models' % len(models))
	return models

# create a feature preparation pipeline for a model
def make_pipeline(model):
	steps = list()
	# standardization
	steps.append(('standardize', StandardScaler()))
	# normalization
	steps.append(('normalize', MinMaxScaler()))
	# the model
	steps.append(('model', model))
	# create pipeline
	pipeline = Pipeline(steps=steps)
	return pipeline

# 进行递归多步预测
def forecast(model, input_x, n_input):
	yhat_sequence = list()
	input_data = [x for x in input_x]
	for j in range(7):
		# prepare the input data
		X = array(input_data[-n_input:]).reshape(1, n_input)
		# make a one-step forecast
		yhat = model.predict(X)[0]
		# add to the result
		yhat_sequence.append(yhat)
		# add the prediction to the input
		input_data.append(yhat)
	return yhat_sequence

# 将多维week数据转成一维序列
def to_series(data):
	# 将数据按照week提取出来
	# data = [array([[]])]->(1,159,7)
	# series = [array([])]->(159,7)
	series = [week[:, 0] for week in data]
	# 将数据展平成一维
	# series = array([])->(1113,)
	series = array(series).flatten()
	return series

# 构造“多对一(7->1)”的监督学习型数据的 输入 输出
def to_supervised(history, n_input):
	# convert history to a univariate series
	data = to_series(history)
	X, y = list(), list()
	ix_start = 0
	# step over the entire history one time step at a time
	for i in range(len(data)):
		#定义每次截取数据的起始和结尾位置
		ix_end = ix_start + n_input
		# ensure we have enough data for this instance
		if ix_end < len(data):
			#截取一周数据
			X.append(data[ix_start:ix_end])
			y.append(data[ix_end])
		# 移动到下一个时间步起始位置
		ix_start += 1
	return array(X), array(y)

# 对模型先拟合，再预测
def sklearn_predict(model, history, n_input):
	# prepare data
	train_x, train_y = to_supervised(history, n_input)
	# make pipeline
	pipeline = make_pipeline(model)
	# 拟合
	pipeline.fit(train_x, train_y)
	# predict the week, recursively
	yhat_sequence = forecast(pipeline, train_x[-1, :], n_input)
	return yhat_sequence

# evaluate a single model
def evaluate_model(model, train, test, n_input):
    # 获取训练集数据history = [array([[]])]->(1,159,7)
    history = [x for x in train]
    predictions = list()
    # 预测测试集中对应的每条数据
    for i in range(len(test)):
        # 对模型先拟合，再预测
        yhat_sequence = sklearn_predict(model, history, n_input)
        # 保存预测结果
        predictions.append(yhat_sequence)
        # get real observation and add to history for predicting the next week
        # history.append(test[i, :])
    predictions = array(predictions)
    # 评估预测值与真实值误差
    score, scores = evaluate_forecasts(test[:, :, 0], predictions)
    return score, scores

# load the new file
dataset = read_csv('household_power_consumption_days.csv', header=0, infer_datetime_format=True, parse_dates=['datetime'], index_col=['datetime'])
# 将数据按week分割成训练集和测试集
train, test = split_dataset(dataset.values)
# 创建模型列表
models = get_models()
n_input = 7
days = ['sun', 'mon', 'tue', 'wed', 'thr', 'fri', 'sat']
# 对每个模型进行评估
for name, model in models.items():
	# evaluate and get scores
	score, scores = evaluate_model(model, train, test, n_input)
	# summarize scores
	summarize_scores(name, score, scores)
	# plot scores
	pyplot.plot(days, scores, marker='o', label=name)
# show plot
pyplot.legend()
#pyplot.show()