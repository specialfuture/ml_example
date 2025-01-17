#!/usr/bin/env python
# encoding: utf-8

"""
@version: 1.0
@author: Liujm
@site:https://github.com/liujm7
@contact: kaka206@163.com
@software: PyCharm
@file: book_recommend_system.py
@time: 2017/9/20 
"""
import numpy as np
import pandas as pd
import copy
import time
from scipy.stats import pearsonr
from sklearn.metrics import pairwise
from scipy.spatial.distance import cosine


def ratings_matrix(dataframe):
    """
    Description:评分记录转化成评分矩阵
    :param dataframe:
    :return:
    """
    n_users = dataframe.user_id.unique().shape[0]
    n_items = dataframe.item_id.unique().shape[0]
    print 'Number of users = ' + str(n_users) + ' | Number of movies = ' + str(n_items)

    # 生成评分矩阵
    data_matrix = np.zeros((n_users, n_items))
    for line in dataframe.itertuples():
        data_matrix[line[1] - 1, line[2] - 1] = line[3]

    return data_matrix


def imputation(inp, Ri):
    """
    Description：未评分的使用替代评分策略，选项包括使用items的平均分和用户的平均分
    :param inp: 选择替代方法:useraverage/itemaverage
    :param Ri: 评分矩阵
    :return:
    """

    Ri = Ri.astype(float)

    def userav():
        """
        Description: 使用用户的已经评分的平均分数代替未评分的位置
        :return:
        """

        for i in xrange(len(Ri)):
            Ri[i][Ri[i] == 0] = sum(Ri[i]) / float(len(Ri[i][Ri[i] > 0]))
        return Ri

    def itemav():
        """
        Description: 使用商品的评分分代替未评分的位置
        :return:
        """

        for i in xrange(len(Ri[0])):
            Ri[:, i][Ri[:, i] == 0] = sum(Ri[:, i]) / float(len(Ri[:, i][Ri[:, i] > 0]))
        return Ri

    switch = {'useraverage': userav(), 'itemaverage': itemav()}
    return switch[inp]


def matrix_sim(matrix, type="cosine"):
    """
    Descriptsion：计算矩阵相关性系数
    :param matrix: 输入的评分矩阵
    :param type: 相关性系数的选型
    :return:
    """
    if type == "cosine":  # 使用余弦距离计算矩阵
        return pairwise.cosine_similarity(matrix, dense_output=True)
    n_rows = len(matrix)
    cor_matrix = np.zeros((n_rows, n_rows))

    for u in xrange(n_rows):  # 使用皮尔逊相关系数计算相关性矩阵
        cor_matrix[u][u] = 1.0
        for v in xrange(u, n_rows):
            cor_matrix[u][v] = sim(matrix[u], matrix[v], metric="pearson")
            cor_matrix[v][u] = cor_matrix[u][v]
    return cor_matrix


def sim(x, y, metric='cosine'):
    """
    Description: 计算相似性
    :param x: 向量x
    :param y: 向量y
    :param metric: 判断使用哪种相似性
    :return:
    """
    if metric == 'cosine':
        return 1 - cosine(x, y)
    else:
        return pearsonr(x, y)[0]


class UserBasedCF(object):
    def __init__(self, data, K=-1, type='cosine'):
        """
        Description: 进行用户协同过滤初始化
        n_items : 商品的数量
        :param data: 评分矩阵
        :param type: 相似性选型
        """
        self.data = data
        self.n_items = len(data[0])
        self.n_uers = len(data)
        self.K = K
        self.user_similarity = matrix_sim(data, type=type)
        self.preds = np.empty((self.n_uers, self.n_items))

    def user_neighs_modify_item_similarity(self):
        """
        Descrption: 根据参数K，选择相似度最高的K个邻居,生成相似度矩阵,邻居的相似度为0.0
        :return:
        """
        user_neighs_similarity = np.zeros((self.n_uers, self.n_uers))
        for i in xrange(self.n_uers):
            items = np.argsort(self.user_similarity[i])[::-1][:self.K]  # 根据相似度逆序返回商品id列表
            items = items[items != i]  # 去掉本身
            for j in xrange(self.n_uers):
                if j in items:  # triangular matrix
                    user_neighs_similarity[i, j] = self.user_similarity[i, j]
        self.user_similarity = user_neighs_similarity

    def CalcRatings(self):
        """
        Description: 计算预测矩阵
        :return:
        """
        if self.K != -1:
            self.user_neighs_modify_item_similarity()
        mean_user_rating = self.data.sum(axis=1, dtype=float) / np.count_nonzero(self.data, axis=1)
        rating_diff = self.data - mean_user_rating[:, np.newaxis]
        self.preds = mean_user_rating[:, np.newaxis] + self.user_similarity.dot(
            rating_diff) / np.array([np.abs(self.user_similarity).sum(axis=1)]).T

    def user_based_user_recommend(self, u, top=10):
        """
        Description:获取某个用户的推荐列表
        :param u:
        :param top:
        :return:
        """
        items_idx = np.argsort(self.preds[u])[::-1]
        cnt = 0
        vec_recs = []
        for i in items_idx:
            if self.data[u, i] == 0 and cnt < top:
                vec_recs.append(i + 1)
                cnt += 1
            elif cnt == top:
                break
        return vec_recs

    def user_based_users_recommend(self, top=10):
        """
        Description: 获取整个用户的推荐字典
        :param top:
        :return:
        """
        recommend_dict = dict()
        for u in xrange(len(self.data)):
            recommend_dict[u] = self.user_based_user_recommend(u, top)

        return recommend_dict


class ItemBasedCF(object):
    def __init__(self, data, K=-1, type='cosine'):
        """
        Description: 进行商品协同过滤初始化
        n_users : 商品的数量
        :param data: 评分矩阵
        :param type: 相似性选型
        """

        self.data = data
        self.item_similarity = matrix_sim(self.data.T, type=type)
        self.n_users = len(self.data)
        self.n_items = len(self.data[0])
        self.K = K
        self.preds = np.empty((self.n_users, self.n_items))

    def item_neighs_modify_item_similarity(self):
        """
        Descrption: K 修改相似性矩阵，最相似的k个item保留相似性系数，其他设置为0
        :return:
        """
        item_neighs_similarity = np.zeros((self.n_items, self.n_items))
        for i in xrange(self.n_items):
            items = np.argsort(self.item_similarity[i])[::-1][:self.K]  # 根据相似度逆序返回商品id列表
            items = items[items != i]  # 去掉本身
            for j in xrange(self.n_items):
                if j in items:  # triangular matrix
                    item_neighs_similarity[i, j] = self.item_similarity[i, j]
        self.item_similarity = item_neighs_similarity

    def CalcRatings(self):
        """
        Description: 计算矩阵分数
        :return:
        """
        if self.K != -1:
            self.item_neighs_modify_item_similarity()
        self.preds = self.data.dot(self.item_similarity) / np.array([np.abs(self.item_similarity).sum(axis=1)])
        self.preds[self.preds > 5] = 5
        self.preds[self.preds < 1] = 1

    def items_based_user_recommend(self, u, top=10):
        """
        Description: 获取某个用户推荐列表
        :param u:
        :param top:
        :return:
        """
        items_idx = np.argsort(self.preds[u])[::-1]
        cnt = 0
        vec_recs = []
        for i in items_idx:
            if self.data[u, i] == 0 and cnt < top:
                vec_recs.append(i + 1)
                cnt += 1
            elif cnt == top:
                break
        return vec_recs

    def items_based_users_recommend(self, top=10):
        """
        Description: 获取所有用户的推荐字典
        :param top:
        :return:
        """
        recommend_dict = {}
        for u in xrange(self.n_users):
            recommend_dict[u] = self.items_based_user_recommend(u, top)
        return recommend_dict


class SlopeOne(object):
    """
    Description : 最简单的基于商品的协同过滤
    """

    def __init__(self, data):
        self.n_users = len(data)
        self.n_items = len(data[0])
        self.difmatrix = np.zeros((self.n_items, self.n_items))
        self.nratings = np.zeros((self.n_items, self.n_items))
        self.data = data
        self.preds = np.empty((self.n_users, self.n_items))

    def build_matrix(self):
        """
        Description: 建立相似性矩阵
        :return:
        """

        n_items = self.n_items
        n_users = self.n_users
        for i in xrange(n_items):
            for j in xrange(i + 1, n_items):
                n_counts = 0
                diff = 0
                for k in xrange(n_users):
                    if self.data[k, i] > 0 and self.data[k, j]:
                        n_counts += 1
                        diff += (self.data[k, i] - self.data[k, j])
                self.difmatrix[i, j] = (diff + 1) / (n_counts + 1)
                self.difmatrix[j, i] = self.difmatrix[i, j]
                self.nratings[i, j] = n_counts
                self.nratings[j, i] = self.nratings[i, j]

    def CalcRatings(self, K=20):
        """
        Description: 计算评分矩阵
        :param K:
        :return:
        """
        self.build_matrix()
        for u in xrange(self.n_users):
            for m in xrange(self.n_items):
                if self.data[u, m] == 0:
                    self.preds[u, m] = np.dot(self.data[u] + self.difmatrix[m], self.nratings[m]) / self.nratings[
                        m].sum()
        self.preds[self.preds > 5] = 5
        self.preds[self.preds < 1] = 1

    def slop_one_user_recommend(self, u, top=10):
        """
        Description: 获取某个用户推荐列表
        :param u:
        :param top:
        :return:
        """
        items_idx = np.argsort(self.preds[u])[::-1]
        cnt = 0
        vec_recs = []
        for i in items_idx:
            if self.data[u, i] == 0 and cnt < top:
                vec_recs.append(i + 1)
                cnt += 1
            elif cnt == top:
                break
        return vec_recs

    def slop_one_users_recommend(self, top=10):
        """
        Description: 获取所有用户的推荐字典
        :param top:
        :return:
        """
        recommend_dict = {}
        for u in xrange(self.n_users):
            recommend_dict[u] = self.slop_one_user_recommend(u, top)
        return recommend_dict


class ModelCF(object):
    """
    Description: 基于模型的协同过滤
    """

    def __init__(self, Umatrix):
        self.Umatirx = Umatrix

    def SGD(self, K, iterations=3, alpha=1, l=0.1, tol=0.001):
        """
        Descrption: Stochastic Gradient Descent 随机梯度下降
        :param K: 特征的数量
        :param iterations: 迭代次数
        :param alpha: 学习速率
        :param l: 正则化系数,防止过拟合
        :param tol: 收敛判据 convergence tolerance
        :return:
        """
        matrix = self.Umatirx
        # 获取矩阵的行数
        n_rows = len(matrix)
        # 获取矩阵的列数
        n_cols = len(matrix)
        # 生成两个随机矩阵
        P = np.random.rand(n_rows, K)
        Q = np.random.rand(n_cols, K)
        Qt = Q.T
        cost = -1
        for it in xrange(iterations):
            for i in xrange(n_rows):
                for j in xrange(n_cols):
                    if matrix[i][j] > 0:
                        # 误差
                        eij = matrix[i][j] - np.dot(P[i, :], Qt[:, j])
                        for k in xrange(K):
                            P[i][k] += np.round(alpha * (2 * eij * Qt[k][j] - l * P[i][k]), 0)
                            Qt[k][j] += np.round(alpha * (2 * eij * P[i][k] - l * Qt[k][j]), 0)
            cost = 0
            for i in xrange(n_rows):
                for j in xrange(n_cols):
                    if matrix[i][j] > 0:
                        cost += pow(matrix[i][j] - np.dot(P[i, :], Qt[:, j]), 2)
                        for k in xrange(K):
                            cost += l * (pow(P[i, k], 2) + pow(Qt[k, j], 2))

            print "第" + str(it) + "迭代,cost:" + str(round(cost, 0))
            # alpha = alpha * 0.9
            if cost < tol:
                break

        return np.round(np.dot(P, Qt), 0)

    def ALS(self, K, iterations=10, l=0.001, tol=0.001):
        """
        Description: Alternating Least Square ALS 交替最小二乘法
        通常没有SGD/SVD精确,但是速度较快，易用于并行计算
        :param K: 特征维数
        :param iterations: 迭代次数
        :param l: 正则化系数
        :param tol: 收敛判据
        :return:
        """
        matrix = self.Umatirx

        n_rows = len(matrix)
        n_cols = len(matrix[0])
        P = np.random.rand(n_rows, K)
        Q = np.random.rand(n_cols, K)
        Qt = Q.T
        matrix = matrix.astype(float)
        mask = matrix > 0
        mask[mask == True] = 1
        mask[mask == False] = 0
        mask = mask.astype(np.float64, copy=False)
        for it in xrange(iterations):
            for u, mask_u in enumerate(mask):
                P[u] = np.linalg.solve(np.dot(Qt, np.dot(np.diag(mask_u), Q)) + l * np.eye(K),
                                       np.dot(Qt, np.dot(np.diag(mask_u), matrix[u].T))).T

            for i, mask_i in enumerate(mask.T):
                Qt[:, i] = np.linalg.solve(np.dot(P.T, np.dot(np.diag(mask_i), P)) + l * np.eye(K),
                                           np.dot(P.T, np.dot(np.diag(mask_i), matrix[:, i])))

            err = np.sqrt(sum(pow(matrix[matrix > 0] - np.dot(P, Qt)[matrix > 0], 2)) / float(len(matrix[matrix > 0])))

            if err < tol:
                break
            print "第" + str(it + 1) + "迭代,cost:" + str(err)

        return np.round(np.dot(P, Qt), 3)

    def NMF_alg(self, K, inp='useraverage', l=0.001):
        """
        Description: Non-negative Matrix Factorization 非负矩阵分解
        :param K: 特征维度
        :param inp: 缺失值替换方法
        :param l: 正则化系数
        :return:
        """
        from sklearn.decomposition import NMF
        matrix = self.Umatirx
        R_tmp = copy.copy(matrix)
        R_tmp = R_tmp.astype(float)
        # inputation
        if inp != 'none':
            R_tmp = imputation(inp, matrix)
        nmf = NMF(n_components=K, alpha=l)
        P = nmf.fit_transform(R_tmp)
        R_tmp = np.dot(P, nmf.components_)
        return np.round(R_tmp, 3)

    def SVD(self, K, inp='useraverage'):
        """
        Description: Singular Value Decomposition 奇异值分解
        :param K: 特征
        :param inp: 缺失值替代方法
        :return:
        """

        from sklearn.decomposition import TruncatedSVD

        matrix = self.Umatirx
        R_tmp = copy.copy(matrix)
        R_tmp = R_tmp.astype(float)
        # inputation
        if inp != 'none':
            R_tmp = imputation(inp, matrix)

        mean_user_rating = R_tmp.sum(axis=1, dtype=float) / np.count_nonzero(R_tmp, axis=1)
        rating_diff = R_tmp - mean_user_rating[:, np.newaxis]
        svd = TruncatedSVD(n_components=K, random_state=4)
        R_k = svd.fit_transform(rating_diff)
        R_tmp = svd.inverse_transform(R_k)
        R_tmp = mean_user_rating[:, np.newaxis] + R_tmp

        return np.round(R_tmp, 3)

    def SVD_EM(self, K, inp='useraverage', iterations=20, tol=0.001):
        """
        Description : SVD+最大期望算法
        :param K: 特征维数
        :param inp: 缺失值替代方法
        :param iterations: 迭代次数
        :param tol: 收敛判据
        :return:
        """

        from sklearn.decomposition import TruncatedSVD
        matrix = self.Umatirx
        R_tmp = copy.copy(matrix)
        n_rows = len(matrix)
        n_cols = len(matrix[0])
        # inputation
        if inp != 'none':
            R_tmp = imputation(inp, matrix)

        # define svd
        svd = TruncatedSVD(n_components=K, random_state=4)
        err = -1
        for it in xrange(iterations):
            # m-step
            R_k = svd.fit_transform(R_tmp)
            R_tmp = svd.inverse_transform(R_k)
            # e-step and error evaluation
            err = np.sqrt(sum(pow(matrix[matrix > 0] - R_tmp[matrix > 0], 2)) / float(len(matrix[matrix > 0])))
            for i in xrange(n_rows):
                for j in xrange(n_cols):
                    if matrix[i][j] > 0:
                        R_tmp[i][j] = matrix[i][j]

            print "第" + str(it + 1) + "迭代,cost:" + str(err)
            if err < tol:
                print it, 'tol reached'
                break
        R_k = svd.fit_transform(R_tmp)
        R_tmp = svd.inverse_transform(R_k)
        return np.round(R_tmp, 3)


class CBF(object):
    """
    Descrption:从描述商品的数中抽取用户特征
    Content-based Filtering 基于内容的过滤
    """

    def __init__(self, data, movies):
        self.ratings_matrix = data.astype('float')
        self.n_features = len(movies[0])
        self.movies = movies

    def CBF_Average(self):
        mean_user_rating = self.ratings_matrix.mean(axis=1, dtype=float)
        ratings_diff = self.ratings_matrix - mean_user_rating[:, np.newaxis]
        V = np.dot(ratings_diff, self.movies) / self.movies.sum(axis=0, dtype=float)[np.newaxis]
        pred = np.dot(V, self.movies.T)
        return pred

    def CBF_regression(self, alpha=0.01, l=0.0001, its=10, tol=0.001):
        n_features = self.n_features + 1
        n_users = len(self.ratings_matrix)
        n_items = len(self.ratings_matrix[0])
        movies_feats = np.ones((n_items, n_features))
        movies_feats[:, 1:] = self.movies
        movies_feats = movies_feats.astype('float')

        p_matrix = np.random.rand(n_users, n_features)
        p_matrix[:, 0] = 1.
        cost = -1
        for it in xrange(its):
            print 'it:', it, ' -- ', cost
            for u in xrange(n_users):
                for f in xrange(n_features):
                    if f == 0:
                        for m in xrange(n_items):
                            if self.ratings_matrix[u, m] > 0:
                                diff = np.dot(p_matrix[u], movies_feats[m]) - self.ratings_matrix[u, m]
                                p_matrix[u, f] += - alpha * (diff * movies_feats[m][f])
                    else:
                        for m in xrange(n_items):
                            if self.ratings_matrix[u, m] > 0:
                                diff = np.dot(p_matrix[u], movies_feats[m]) - self.ratings_matrix[u, m]
                                p_matrix[u, f] += -alpha * (diff * movies_feats[m][f]) + l * p_matrix[u, f]
            preds = np.dot(p_matrix, movies_feats.T)
            cost = np.sqrt(
                sum(pow(self.ratings_matrix[self.ratings_matrix > 0] - preds[self.ratings_matrix > 0], 2)) / float(
                    len(self.ratings_matrix[self.ratings_matrix > 0])))
            print 'err', cost
            if cost < tol:
                print 'err', cost
                break
        preds = np.dot(p_matrix, movies_feats.T)
        preds[preds > 5] = 5
        preds[preds < 1] = 1
        return preds


class AssociationRules(object):
    """
    Description: 关联规则
    """

    def __init__(self, Umatrix, Movieslist, min_support=0.1, min_confidence=0.1, likethreshold=3):
        """
        Description: 关联规则初始化
        :param Umatrix: 评分矩阵
        :param Movieslist: 电影列表
        :param min_support: 支持度
        :param min_confidence: 置信度
        :param likethreshold: 下限的过滤分数
        """
        self.min_support = min_support  # 支持度
        self.min_confidence = min_confidence  # 置信度
        self.Movieslist = Movieslist  # 电影清单
        n_items = len(Umatrix[0])
        transactions = []  # 项集
        for u in Umatrix:
            # 评分>likethreshold  才能构成项集
            s = [i for i in xrange(len(u)) if u[i] > likethreshold]
            if len(s) > 0:
                transactions.append(s)
        # 将所有的item展开成一行
        flat = [item for sublist in transactions for item in sublist]
        # 初始化的items
        inititems = map(frozenset, [[item] for item in frozenset(flat)])
        # 将项集转化成无需集合
        set_trans = map(set, transactions)
        # 过滤出在关联规则组合中出现的元素
        sets_init, self.dict_sets_support = self.filterSet(set_trans, inititems)
        # 推荐系统只需要两项关联规则
        setlen = 2
        # 构建所有可能出现的组合
        items_temp = self.combine_lists(sets_init, setlen)
        # 过滤出所有的频繁集和支持度
        self.freq_sets, sup_tmp = self.filterSet(set_trans, items_temp)
        # 更新支持度集合
        self.dict_sets_support.update(sup_tmp)
        # 关联规则置信度矩阵初始化
        self.ass_matrix = np.zeros((n_items, n_items))
        # 构建关联规则置信度矩阵，遍历频繁集
        for freqset in self.freq_sets:
            list_setitems = [frozenset([item]) for item in freqset]
            self.calc_confidence_matrix(freqset, list_setitems)

    def filterSet(self, set_trans, likeditems):
        """
        Description: 过滤出组合中出现的元素
        :param set_trans: 给定的项集
        :param likeditems: 所有的元素
        :return:
        """
        itemscnt = {}
        # 遍历给定同时出现的项集
        for id in set_trans:
            # 遍历所有可能的元素
            for item in likeditems:
                # 如果某一个元素出现在某一个项里面
                if item.issubset(id):
                    # 统计元素出现的次数
                    itemscnt.setdefault(item, 0)
                    itemscnt[item] += 1
        # 计算多少个项集合
        num_items = float(len(set_trans))
        # 频繁集
        freq_sets = []
        # 支持度集
        dict_sets = {}
        # 遍历每个元素出现的次数
        for key in itemscnt:
            # 计算key 对应的支持度
            support = itemscnt[key] / num_items
            if support >= self.min_support:  # 如果支持度大于设定的支持度
                freq_sets.insert(0, key)
            # 插入支持度
            dict_sets[key] = support
        return freq_sets, dict_sets

    def combine_lists(self, freq_sets, setlen):
        """
        Description: 寻找所有的可能, 当setlen=2，寻找可能同时出现的两个商品组合
        :param freq_sets: 遍历的商品组合，setlen=2 的时候，就是单个元素集合
        :param setlen: 可能的组合长度
        :return:
        """
        set_items_list = []
        n_sets = len(freq_sets)
        for i in xrange(n_sets):
            for j in xrange(i + 1, n_sets):
                set_list1 = list(freq_sets[i])[:setlen - 2]
                set_list2 = list(freq_sets[j])[:setlen - 2]
                if set(set_list1) == set(set_list2):
                    # 计算并集 union
                    set_items_list.append(freq_sets[i].union(freq_sets[j]))
        return set_items_list

    def calc_confidence_matrix(self, freqset, list_setitems):
        """
        Description: 计算相似性矩阵
        :param freqset: 某一项频繁集
        :param list_setitems: 频繁集内部的单个元素项的列表
        :return:
        """
        # 遍历推荐的商品(traget:目标)
        for target in list_setitems:
            # self.dict_sets_support[freqset]同时出现的项集的支持度
            # self.dict_sets_support[freqset - target] 已经打分的项集的支持度
            # 计算基于已经打分的商品的支持度下，推荐商品的置信度
            confidence = self.dict_sets_support[freqset] / self.dict_sets_support[freqset - target]
            # 大于最低的置信度
            if confidence > self.min_confidence:
                self.ass_matrix[list(freqset)[0]][list(target)[0]] = confidence

    def GetRecItems(self, u_vec, indxs=False):
        """
        Description: 计算某个向量的推荐的商品列表
        :param u_vec: 给定的用户
        :param indxs: false过滤掉已经看过的商品
        :return:
        """
        vec_recs = np.dot(u_vec, self.ass_matrix)
        sortedweight = np.argsort(vec_recs)
        seenindxs = [indx for indx in xrange(len(u_vec)) if u_vec[indx] > 0]
        seenmovies = np.array(self.Movieslist)

        recitems = np.array(self.Movieslist)[sortedweight]
        recitems = [m for m in recitems if m in seenmovies]
        if indxs:
            vec_recs[seenindxs] = -1
            recsvec = np.argsort(vec_recs)[::-1][np.argsort(vec_recs) > 0]
            return recsvec
        return recitems[::-1]


class Hybrid_cbf_cf(object):
    """
    Description: 组合协同过滤和基于内容过滤，将内容的平均分特征补充到效用矩阵里面
    """

    def __init__(self, Movies, Movieslist, Umatrix):
        """
        Description: 构造器生成新的效用矩阵，为每位用户增加了他为每种类型的电影打的平均分特征
        :param Movies: 商品的特征矩阵
        :param Movieslist: 商品的list
        :param Umatrix: 评分矩阵
        """
        self.n_features = len(Movies[0])  # 商品特征
        self.Movielist = Movieslist  # 商品列表
        self.Movies = Movies.astype(float)
        self.Umatrix = Umatrix  # 评分矩阵
        # 初始化新的效用矩阵
        self.Umatrix_mfeats = np.zeros((len(Umatrix), len(Umatrix[0]) + self.n_features))
        # 计算用户的平均分
        mean_user_rating = Umatrix.sum(axis=1, dtype=float) / np.count_nonzero(Umatrix, axis=1)
        # 用户评分减去平均分
        diffs = Umatrix - mean_user_rating[:, np.newaxis]
        diffs[diffs == (-mean_user_rating[:, np.newaxis])] = 0
        # 将用户评分放到了新的效用矩阵里
        self.Umatrix_mfeats[:, :len(Umatrix[0])] = diffs
        self.n_movies = len(Movies)
        # 循环每个用户将用户每种类型的平均分也放到新的效用矩阵中
        for u in xrange(len(Umatrix)):
            u_vec = Umatrix[u]
            self.Umatrix_mfeats[u, len(Umatrix[0]):] = self.GetUserItemFeatures(u_vec)

    def GetUserItemFeatures(self, u_vec):
        """
        Description: 获取每个用户的类型平均分
        :param u_vec: 用户向量
        :return:
        """
        # 计算每个用户的平均分
        mean_u = u_vec[u_vec > 0].mean()
        # 计算每个用户的偏差分
        diff_u = u_vec - mean_u
        features_u = np.zeros(self.n_features).astype(float)
        cnts = np.zeros(self.n_features)
        for m in xrange(self.n_movies):
            if u_vec[m] > 0:
                # 计算特征加权分数
                features_u += self.Movies[m] * diff_u[m]
                cnts += self.Movies[m]
        for m in xrange(0, self.n_features):
            # 计算平均分
            if cnts[m] > 0:
                features_u[m] = features_u[m] / cnts[m]
        return features_u

    def CalcRatings(self, type='cosine', top=10):
        """
        Description: 计算预测矩阵，并进行推荐
        :param type:
        :return:
        """
        # 计算了整个矩阵相关性矩阵
        user_mfeats_similarity = matrix_sim(self.Umatrix_mfeats, type)
        # 计算偏差值矩阵
        mean_user_rating = self.Umatrix.sum(axis=1, dtype=float) / np.count_nonzero(self.Umatrix, axis=1)
        rating_diff = self.Umatrix - mean_user_rating[:, np.newaxis]
        rating_diff[rating_diff == (-mean_user_rating[:, np.newaxis])] = 0
        # 计算预测值矩阵
        pred = mean_user_rating[:, np.newaxis] + user_mfeats_similarity.dot(
            rating_diff) / np.array([np.abs(user_mfeats_similarity).sum(axis=1)]).T
        pred[pred > 5] = 5
        pred[pred < 1] = 1
        # 推荐商品
        recommend_dict_all = dict()
        for u in xrange(len(self.Umatrix)):
            items_idx = np.argsort(pred[u])[::-1]
            recommend_dict = dict()
            cnt = 0
            for i in items_idx:
                if self.Umatrix[u, i] == 0 and cnt < top:
                    recommend_dict[i + 1] = pred[u, i]
                    cnt += 1
                elif cnt == top:
                    break
            recommend_dict_all[u] = recommend_dict

        return pred, recommend_dict_all


class Hybird_svd(object):
    """
    Description: 混合方法,将svd生成的特征和评分矩阵组合起来
    """

    def __init__(self, Moives, Movieslist, Umatrix, K, inp='useraverage'):
        from sklearn.decomposition import TruncatedSVD
        self.n_features = len(Moives[0])
        self.Movieslist = Movieslist
        self.Movies = Moives.astype(float)
        R_tmp = copy.copy(Umatrix)
        R_tmp = R_tmp.astype(float)

        if inp != 'none':
            R_tmp = imputation(inp, Umatrix)
        Umatrix_mfeats = np.zeros((len(Umatrix), len(Umatrix[0]) + self.n_features))
        # 计算用户的平均分
        mean_user_rating = Umatrix.sum(axis=1, dtype=float) / np.count_nonzero(Umatrix, axis=1)
        # 用户评分减去平均分
        diffs = R_tmp - mean_user_rating[:, np.newaxis]
        diffs[diffs == (-mean_user_rating[:, np.newaxis])] = 0
        self.n_movies = len(Moives)
        Umatrix_mfeats[:, :len(Umatrix[0])] = diffs

        # 循环每个用户将用户每种类型的平均分也放到新的效用矩阵中
        for u in xrange(len(Umatrix)):
            u_vec = Umatrix[u]
            Umatrix_mfeats[u, len(Umatrix[0]):] = self.GetUserItemFeatures(u_vec)

        svd = TruncatedSVD(n_components=K, random_state=4)
        R_k = svd.fit_transform(Umatrix_mfeats)
        R_tmp = mean_user_rating[:, np.newaxis] + svd.inverse_transform(R_k)
        self.matrix = np.round(R_tmp[:, :self.n_movies], 3)
        self.matrix[self.matrix > 5] = 5
        self.matrix[self.matrix < 1] = 1

    def GetUserItemFeatures(self, u_vec):
        """
        Description: 获取每个用户的类型平均分
        :param u_vec: 用户向量
        :return:
        """
        # 计算每个用户的平均分
        mean_u = u_vec[u_vec > 0].mean()
        # 计算每个用户的偏差分
        diff_u = u_vec - mean_u
        features_u = np.zeros(self.n_features).astype(float)
        cnts = np.zeros(self.n_features)
        for m in xrange(self.n_movies):
            if u_vec[m] > 0:
                # 计算特征加权分数
                features_u += self.Movies[m] * diff_u[m]
                cnts += self.Movies[m]
        for m in xrange(0, self.n_features):
            # 计算平均分
            if cnts[m] > 0:
                features_u[m] = features_u[m] / cnts[m]
        return features_u


def cross_validation(matrix, k):
    """
    Description: 交叉分训练集合测试集合，伪随机
    :param df: dataframe
    :param k: 交叉验证次数
    :return:
    """
    val_num = int(len(matrix) / float(k))
    print val_num
    np_trains = []
    np_vals = []
    for i in xrange(k):
        start_val = (k - i - 1) * val_num
        end_val = start_val + val_num
        np_trains.append(np.vstack([matrix[:start_val], matrix[end_val:]]))
        np_vals.append(matrix[start_val:end_val])
    return np_trains, np_vals


def HideRandomRtings(u_vec, ratiovals=0.5):
    """
    Descripion: 随机隐藏半数电影的分数，以便预测他们的实际值
    :param u_vec: 每个用户的分数向量
    :param ratiovals: 隐藏评分的比例
    :return:
    """

    import random
    u_test = np.zeros(len(u_vec))  # 存储用于测试算法的实际分数
    u_vals = np.zeros(len(u_vec))  # 存储预测值
    cnt = 0
    n_ratings = len(u_vec[u_vec > 0])
    for i in xrange(len((u_vec))):
        if u_vec[i] > 0:
            if bool(random.getrandbits(1)) or cnt >= int(n_ratings * ratiovals):
                u_test[i] = u_vec[i]
            else:
                cnt += 1
                u_vals[i] = u_vec[i]
    return u_test, u_vals


class Evaluate(object):
    """
    Description: 评估,进行各个推荐算法的效果比较
    """

    def __init__(self):
        """
        Description: 数据处理
        """

        import os
        os.chdir("D:\\work\\liujm\\2017\\9\\20170911\\ml-100k\\ml-100k")
        # os.chdir("D:\\work\\liujm\\2017\\9\\20170919\\ml-20m\\ml-20m")
        header = ['user_id', 'item_id', 'rating', 'timestamp']
        # df = pd.read_csv(".\\ml-100k\u.data", sep="\t", names=header)
        # df = pd.read_csv(".\\ratings.csv", sep=',', names=header)
        df = pd.read_csv(".\\u.data", sep="\t", names=header)
        data_matrix = ratings_matrix(df)
        self.data_matrix = data_matrix
        df_info_header = ['movie_id', 'movie title', 'release date', 'video release date', 'IMDb URL', 'unknown',
                          'Action',
                          'Adventure', 'Animation', 'Children\'s', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy',
                          'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War',
                          'Western']

        df_info = pd.read_csv('.\\u.item', sep='|', names=df_info_header)

        moviescats = ['unknown', 'Action', 'Adventure', 'Animation', 'Children\'s', 'Comedy', 'Crime', 'Documentary',
                      'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical', 'Mystery',
                      'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']
        dfout_movies = pd.DataFrame(columns=['movie_id'] + moviescats)
        startcatsindx = 5

        # matrix movies's content
        cnt = 0
        movies_list = df_info.movie_id.unique()
        n_movies = len(movies_list)
        n_features = len(moviescats)
        content_matrix = np.zeros((n_movies, n_features))
        for x in xrange(n_movies):
            content_matrix[x] = df_info.iloc[x][startcatsindx:].tolist()

        self.content_matrix = content_matrix
        self.movies_list = movies_list

        self.n_folds = 5
        self.np_trains, self.np_vals = cross_validation(data_matrix, self.n_folds)
        n_movies = len(data_matrix[0])
        self.vals_vecs_folds = []
        self.tests_vecs_folds = []
        for i in xrange(self.n_folds):
            u_vecs = self.np_vals[i]
            v_tests = np.empty((0, n_movies), dtype=float)
            vvals = np.empty((0, n_movies), dtype=float)
            for u_vec in u_vecs:
                u_test, u_vals = HideRandomRtings(u_vec)
                vvals = np.vstack([vvals, u_vals])
                v_tests = np.vstack([v_tests, u_test])
            self.vals_vecs_folds.append(vvals)
            self.tests_vecs_folds.append(v_tests)

    def user_recommend(self, preds, u, top=10):
        """
        Description: 获取某个用户推荐列表
        :param u:
        :param top:
        :return:
        """
        items_idx = np.argsort(preds[u])[::-1]
        cnt = 0
        vec_recs = []
        for i in items_idx:
            if self.data_matrix[u, i] == 0 and cnt < top:
                vec_recs.append(i + 1)
                cnt += 1
            elif cnt == top:
                break
        return vec_recs

    def users_recommend(self, preds, n_users, top=10):
        """
        Description: 获取所有用户的推荐字典
        :param top:
        :return:
        """
        recommend_dict = {}
        for u in xrange(n_users):
            recommend_dict[u] = self.user_recommend(preds, u, top)
        return recommend_dict

    def evaluate(self):
        """
        Description:评估评分推荐
        :return:
        """
        err_itembased = 0.
        cnt_itembased = 0
        err_userbased = 0.
        cnt_userbased = 0
        err_slopeone = 0.
        cnt_slopeone = 0
        err_cbfcf = 0.
        cnt_cbfcf = 0
        rmse_itembased = []
        rmse_userbased = []
        for i in xrange(self.n_folds):
            Umatrix = self.np_trains[i]
            val_matrix = self.np_vals[i]

            # 基于商品的协同过滤
            cfitembased = ItemBasedCF(Umatrix)
            cfitembased.item_neighs_modify_item_similarity()
            preds_itembased = np.dot(val_matrix, cfitembased.item_similarity)
            cnt_itembased = len(val_matrix[val_matrix > 0])
            err_itembased = sum(pow(val_matrix[val_matrix > 0] - preds_itembased[val_matrix > 0], 2))
            rmse_itembased.append(np.sqrt(err_itembased / float(cnt_itembased)))

        # rmse_userbased_avg = sum(rmse_userbased) / float(len(rmse_userbased))
        rmse_itembased_avg = sum(rmse_itembased) / float(len(rmse_itembased))
        # print "rmse_userbased_avg:", rmse_userbased_avg
        print cnt_itembased
        print err_itembased
        print "rmse_itembased_avg:", rmse_itembased_avg

    def rmse_evaluate(self):
        """
        Description:整体评估所有的方法
        :return:
        """
        # 基于用户推荐
        cfitembased = ItemBasedCF(self.data_matrix)
        cfitembased.item_neighs_modify_item_similarity()
        preds_itembased = np.dot(self.data_matrix, cfitembased.item_similarity)
        preds_itembased[preds_itembased > 5] = 5
        preds_itembased[preds_itembased < 1] = 1
        cnt_itembased = len(self.data_matrix[self.data_matrix > 0])
        err_itembased = sum(pow(self.data_matrix[self.data_matrix > 0] - preds_itembased[self.data_matrix > 0], 2))
        rmse_itembased = np.sqrt(err_itembased / float(cnt_itembased))

        # 基于用户推荐
        cfuserbased = UserBasedCF(self.data_matrix)
        cfuserbased.user_neighs_modify_item_similarity()
        preds_userbased = np.dot(cfuserbased.user_similarity, self.data_matrix)
        preds_userbased[preds_userbased > 5] = 5
        preds_userbased[preds_userbased < 1] = 1
        cnt_userbased = len(self.data_matrix[self.data_matrix > 0])
        err_userbased = sum(pow(self.data_matrix[self.data_matrix > 0] - preds_userbased[self.data_matrix > 0], 2))
        rmse_userbased = np.sqrt(err_userbased / float(cnt_userbased))

        # 基于模型推荐
        modelcf = ModelCF(self.data_matrix)
        preds_ALS = modelcf.ALS(10)
        preds_userbased[preds_ALS > 5] = 5
        preds_userbased[preds_ALS < 1] = 1
        rmse_ALS = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - preds_ALS[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))
        preds_NMF = modelcf.NMF_alg(30)
        preds_NMF[preds_NMF > 5] = 5
        preds_NMF[preds_NMF < 1] = 1
        rmse_NMF = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - preds_NMF[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))

        preds_SVD = modelcf.SVD(30)
        preds_NMF[preds_SVD > 5] = 5
        preds_NMF[preds_SVD < 1] = 1
        rmse_SVD = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - preds_SVD[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))
        preds_SVD_EM = modelcf.SVD_EM(30)
        preds_SVD_EM[preds_SVD_EM > 5] = 5
        preds_SVD_EM[preds_SVD_EM < 1] = 1

        rmse_SVD_EM = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - preds_SVD_EM[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))

        # 基于混合模型
        hybird_svd = Hybird_svd(self.content_matrix, self.movies_list, self.data_matrix, 10)
        preds_hybird_svd = hybird_svd.matrix
        preds_hybird_svd[preds_hybird_svd > 5] = 5
        preds_hybird_svd[preds_hybird_svd < 1] = 1

        rmse_hybird_svd = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - preds_hybird_svd[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))

        hybrid_cbf_cf = Hybrid_cbf_cf(self.content_matrix, self.movies_list, self.data_matrix)
        pred_hybrid_cbf_cf, recommend_dict_all = hybrid_cbf_cf.CalcRatings()
        pred_hybrid_cbf_cf[pred_hybrid_cbf_cf > 5] = 5
        pred_hybrid_cbf_cf[pred_hybrid_cbf_cf < 1] = 1
        rmse_hybrid_cbf_cf = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - pred_hybrid_cbf_cf[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))

        # 基于内容
        cbf = CBF(self.data_matrix, self.content_matrix)
        pred_cbf_regression = cbf.CBF_regression()
        pred_cbf_regression[pred_cbf_regression > 5] = 5
        pred_cbf_regression[pred_cbf_regression < 1] = 1
        rmse_pred_cbf_regression = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - pred_cbf_regression[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))
        pred_cbf_average = cbf.CBF_Average()
        pred_cbf_average[pred_cbf_average > 5] = 5
        pred_cbf_average[pred_cbf_average < 1] = 1
        rmse_pred_cbf_average = np.sqrt(
            sum(pow(self.data_matrix[self.data_matrix > 0] - pred_cbf_average[self.data_matrix > 0], 2)) / float(
                len(self.data_matrix[self.data_matrix > 0])))

        print "rmse_itembased", rmse_itembased
        print "rmse_userbased:", rmse_userbased
        print "rmse_ALS:", rmse_ALS
        print "rmse_NMF:", rmse_NMF
        print "rmse_SVD:", rmse_SVD
        print "rmse_SVD_EM:", rmse_SVD_EM
        print "rmse_hybird_svd:", rmse_hybird_svd
        print "rmse_hybrid_cbf_cf:", rmse_hybrid_cbf_cf
        print "rmse_pred_cbf_regression:", rmse_pred_cbf_regression
        print "rmse_pred_cbf_average:", rmse_pred_cbf_average

    def precision_recall_fscore_method(self, preds):
        from sklearn.metrics import precision_recall_fscore_support
        real_ratings_class = [1 if x >= 3 else 0 for x in self.data_matrix[self.data_matrix > 0]]
        pred_ratings_class = [1 if x >= 3 else 0 for x in preds[self.data_matrix > 0]]
        precision, recall, fbeta_score, support = precision_recall_fscore_support(real_ratings_class,
                                                                                  pred_ratings_class)
        return precision, recall, fbeta_score, support

    def classfication_metric_evaluate(self):
        # 基于用户推荐
        cfitembased = ItemBasedCF(self.data_matrix, K=20)
        cfitembased.CalcRatings()
        preds_itembased = cfitembased.preds

        # 基于用户推荐
        cfuserbased = UserBasedCF(self.data_matrix, K=20)
        cfuserbased.CalcRatings()
        preds_userbased = cfuserbased.preds

        # 基于模型推荐
        modelcf = ModelCF(self.data_matrix)
        preds_ALS = modelcf.ALS(20)

        preds_NMF = modelcf.NMF_alg(30)

        preds_SVD = modelcf.SVD(30)

        preds_SVD_EM = modelcf.SVD_EM(30)

        # 基于混合模型
        hybird_svd = Hybird_svd(self.content_matrix, self.movies_list, self.data_matrix, 10)
        preds_hybird_svd = hybird_svd.matrix

        hybrid_cbf_cf = Hybrid_cbf_cf(self.content_matrix, self.movies_list, self.data_matrix)
        pred_hybrid_cbf_cf, recommend_dict_all = hybrid_cbf_cf.CalcRatings()

        # 基于内容
        cbf = CBF(self.data_matrix, self.content_matrix)
        pred_cbf_regression = cbf.CBF_regression()

        pred_cbf_average = cbf.CBF_Average()
        pred_cbf_average[pred_cbf_average > 5] = 5
        pred_cbf_average[pred_cbf_average < 1] = 1

        preds_dict = {}
        preds_dict['preds_itembased'] = preds_itembased
        preds_dict['preds_userbased'] = preds_userbased
        preds_dict['preds_ALS'] = preds_ALS
        preds_dict['preds_NMF'] = preds_NMF
        preds_dict['preds_SVD'] = preds_SVD
        preds_dict['preds_SVD_EM'] = preds_SVD_EM
        preds_dict['pred_cbf_regression'] = pred_cbf_regression
        preds_dict['pred_cbf_average'] = pred_cbf_average
        preds_dict['pred_hybrid_cbf_cf'] = pred_hybrid_cbf_cf
        preds_dict['preds_hybird_svd'] = preds_hybird_svd
        for key, preds in preds_dict.iteritems():
            precision, recall, fbeta_score, support = self.precision_recall_fscore_method(preds)
            print key + "|precision:" + str(precision) + "|recall:" + str(recall) + "|f1:" + str(
                fbeta_score) + "|support:" + str(support)


class Main:
    def __init__(self):
        import os
        os.chdir("D:\\work\\liujm\\2017\\9\\20170911\\ml-100k\\ml-100k")
        # os.chdir("D:\\work\\liujm\\2017\\9\\20170919\\ml-20m\\ml-20m")
        header = ['user_id', 'item_id', 'rating', 'timestamp']
        # df = pd.read_csv(".\\ml-100k\u.data", sep="\t", names=header)
        # df = pd.read_csv(".\\ratings.csv", sep=',', names=header)
        df = pd.read_csv(".\\u.data", sep="\t", names=header)
        data_matrix = ratings_matrix(df)
        self.data_matrix = data_matrix
        df_info_header = ['movie_id', 'movie title', 'release date', 'video release date', 'IMDb URL', 'unknown',
                          'Action',
                          'Adventure', 'Animation', 'Children\'s', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy',
                          'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War',
                          'Western']

        df_info = pd.read_csv('.\\u.item', sep='|', names=df_info_header)

        moviescats = ['unknown', 'Action', 'Adventure', 'Animation', 'Children\'s', 'Comedy', 'Crime', 'Documentary',
                      'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical', 'Mystery',
                      'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']
        dfout_movies = pd.DataFrame(columns=['movie_id'] + moviescats)
        startcatsindx = 5

        # matrix movies's content
        cnt = 0
        movies_list = df_info.movie_id.unique()
        n_movies = len(movies_list)
        n_features = len(moviescats)
        content_matrix = np.zeros((n_movies, n_features))
        for x in xrange(n_movies):
            content_matrix[x] = df_info.iloc[x][startcatsindx:].tolist()

        self.content_matrix = content_matrix
        self.movies_list = movies_list

    def test_model(self):
        dm = ModelCF(self.data_matrix)
        pred = dm.SVD_EM(K=10)
        mask = self.data_matrix > 0
        mask[mask == True] = 1
        mask[mask == False] = 0
        err = np.sum((mask * (self.data_matrix - pred) ** 2))
        print err

    def test_cf(self):
        print "time.time(): %f " % time.time()
        dm = UserBasedCF(self.data_matrix)
        recommend_dict_all = dm.users_based_recommend(top=20)
        print recommend_dict_all.get(0, [])
        print "time.time(): %f " % time.time()

    def test_cbf(self):
        cbf = CBF(self.data_matrix, self.content_matrix)
        pred = cbf.CBF_regression()
        # keys = [x for x in xrange(n_movies)]

        items_idx = np.argsort(pred[1])[::-1]
        recommend_dict = dict()
        cnt = 0
        top = 10
        for i in items_idx:
            if self.data_matrix[1, i] == 0 and cnt < top:
                recommend_dict[i + 1] = pred[1, i]
                cnt += 1
            elif cnt == top:
                break
        # recommend_dict_all[u] = recommend_dict
        print recommend_dict

    def test_slopone(self):
        so = SlopeOne(self.data_matrix)
        pred = so.slop_one_recommend()
        # keys = [x for x in xrange(n_movies)]

        items_idx = np.argsort(pred[1])[::-1]
        recommend_dict = dict()
        cnt = 0
        top = 10
        for i in items_idx:
            if self.data_matrix[1, i] == 0 and cnt < top:
                recommend_dict[i + 1] = pred[1, i]
                cnt += 1
            elif cnt == top:
                break
        # recommend_dict_all[u] = recommend_dict
        print recommend_dict.get()

    def test_Hybrid_cbf_cf(self):
        h_cbf_cf = Hybrid_cbf_cf(self.content_matrix, self.movies_list, self.data_matrix)
        recommend_dict_all = h_cbf_cf.CalcRatings()
        print recommend_dict_all.get(0, [])

    def test_AssociationRules(self):
        ass = AssociationRules(self.data_matrix, self.movies_list)
        movie_list = ass.GetRecItems(self.data_matrix[0])
        print min(movie_list)
        # print movie_list
        print len(movie_list)

    def test_Hybird_svd(self):
        h_svd = Hybird_svd(self.content_matrix, self.movies_list, self.data_matrix, 10, 'none')
        print h_svd.matrix[0]


if __name__ == '__main__':
    # test = Main()
    # test.test_Hybird_svd()
    ev = Evaluate()
    ev.classfication_metric_evaluate()
