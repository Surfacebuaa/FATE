#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import pandas as pd
from fate.arch.dataframe import PandasReader, DataFrame
from fate.arch import Context
import sys
from fate.ml.ensemble.algo.secureboost.hetero.guest import HeteroSecureBoostGuest
from fate.ml.ensemble.algo.secureboost.hetero.host import HeteroSecureBoostHost
from datetime import datetime


def get_current_datetime_str():
    return datetime.now().strftime("%Y-%m-%d-%H-%M")


arbiter = ("arbiter", "10000")
guest = ("guest", "10000")
host = ("host", "9999")
name = get_current_datetime_str()


def create_ctx(local):
    from fate.arch import Context
    from fate.arch.computing.backends.standalone import CSession
    from fate.arch.federation.backends.standalone import StandaloneFederation
    import logging

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    computing = CSession()
    return Context(
        computing=computing, federation=StandaloneFederation(computing, name, local, [guest, host, arbiter])
    )


if __name__ == "__main__":
    party = sys.argv[1]
    max_depth = 3
    num_tree = 10
    from sklearn.metrics import roc_auc_score as auc

    if party == "guest":
        ctx = create_ctx(guest)
        df = pd.read_csv("./../../../../../../../examples/data/student_hetero_guest.csv")
        df["sample_id"] = [i for i in range(len(df))]

        reader = PandasReader(sample_id_name="sample_id", match_id_name="id", label_name="y", dtype="float32")

        data_guest = reader.to_frame(ctx, df)

        trees = HeteroSecureBoostGuest(num_tree, max_depth=max_depth, objective="regression:l2")
        trees.fit(ctx, data_guest)
        pred = trees.get_train_predict().as_pd_df()
        pred["sample_id"] = pred.sample_id.astype(int)
        df = pd.merge(df, pred, on="sample_id")

        # load tree
        # tree_dict = pickle.load(open('guest_tree.pkl', 'rb'))
        # trees.from_model(tree_dict)
        pred_ = trees.predict(ctx, data_guest).as_pd_df()
        pred_.sample_id = pred_.sample_id.astype(int)
        merge_df = pd.merge(pred, pred_, on="sample_id")
        from sklearn.metrics import mean_squared_error

        print(mean_squared_error(pred.predict_score, pred.label))
        print((pred.predict_score - pred_.predict_score).sum())

    elif party == "host":
        ctx = create_ctx(host)

        df_host = pd.read_csv("./../../../../../../../examples/data/student_hetero_host.csv")
        df_host["sample_id"] = [i for i in range(len(df_host))]

        reader_host = PandasReader(sample_id_name="sample_id", match_id_name="id", dtype="float32")

        data_host = reader_host.to_frame(ctx, df_host)

        trees = HeteroSecureBoostHost(num_tree, max_depth=max_depth)
        trees.fit(ctx, data_host)
        # load tree
        # tree_dict = pickle.load(open('host_tree.pkl', 'rb'))
        # trees.from_model(tree_dict)
        trees.predict(ctx, data_host)
