from flask import Flask, render_template, request, jsonify
import sqlalchemy as sql
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import pymysql
import json
import pandas as pd
from flask import Response
import os
from surprise import dump


# Path to dump files and name
dumpfile_knn = os.path.join("./data/dump/dump_knn_dump_file")
beer_pickel_path = os.path.join("./data/dump/beer_final.pkl")

# Load dump files
predictions_knn, algo_knn = dump.load(dumpfile_knn)
beers_df = pd.read_pickle(beer_pickel_path)
beers_df["beer_brewery"] = beers_df["beer_brewery"].replace("/", "-", regex=True)

# Create the trainset from the knn_algorithm in order to get the inner_ids
trainset_knn = algo_knn.trainset


def get_beer_brewery(beer_raw_id):
    beer_brewery = beers_df.loc[beers_df.beer_id == beer_raw_id, "beer_brewery"].values[0]
    return beer_brewery


def get_beer_raw_id(beer_name):
    beer_raw_id = beers_df.loc[beers_df.beer_brewery == beer_name, "beer_id"].values[0]
    return beer_raw_id


def get_beer_style(beer_raw_id):
    beer_style = beers_df.loc[beers_df.beer_id == beer_raw_id, "style"].values[0]
    return beer_style


def get_beer_score_mean(beer_raw_id):
    score_mean = beers_df.loc[beers_df.beer_id == beer_raw_id, "score"].values[0]
    return score_mean


def get_beer_neighbors(beer_raw_id):
    beer_inner_id = algo_knn.trainset.to_inner_iid(beer_raw_id)
    beer_neighbors = algo_knn.get_neighbors(beer_inner_id, k=10)
    beer_neighbors = (
        algo_knn.trainset.to_raw_iid(inner_id) for inner_id in beer_neighbors
    )
    return beer_neighbors


def get_beer_recc_df(beer_raw_id):
    beer_inner_id = algo_knn.trainset.to_inner_iid(beer_raw_id)
    beer_neighbors = algo_knn.get_neighbors(beer_inner_id, k=10)
    beer_neighbors = (
        algo_knn.trainset.to_raw_iid(inner_id) for inner_id in beer_neighbors
    )
    beers_id_recc = []
    beer_brewery_recc = []
    beer_style_recc = []
    beer_score_mean = []
    for beer in beer_neighbors:
        beers_id_recc.append(beer)
        beer_brewery_recc.append(get_beer_brewery(beer))
        beer_style_recc.append(get_beer_style(beer))
        beer_score_mean.append(get_beer_score_mean(beer))
    beer_reccomendations_df = pd.DataFrame(
        list(zip(beers_id_recc, beer_brewery_recc, beer_style_recc, beer_score_mean)),
        columns=["beer_id", "name", "style", "score_mean"],
    )
    return beer_reccomendations_df


################################################################
#               Flask Setup and Database Connection            #
################################################################
app = Flask(__name__)

SQLALCHEMY_DATABASE_URL = os.getenv("DB_CONN")

sql_engine = sql.create_engine(SQLALCHEMY_DATABASE_URL)

################################################################
#                        Flask Routes                          #
################################################################


@app.route("/")
def home():
    return render_template("verification.html")


@app.route("/index.html")
def index():
    return render_template("index.html")


@app.errorhandler(404)
def invalid_route(e):
    return render_template("404.html")


# --------------------------------------------------------------#
#                       recommender routes                     #
# --------------------------------------------------------------#


@app.route("/educator.html")
def educator():
    TABLENAME = "ba_beerstyles"
    query = f"SELECT DISTINCT Category FROM {TABLENAME}"
    df = pd.read_sql_query(query, sql_engine)
    categories = df["Category"].tolist()
    categories.append("Choose a Category")
    return render_template("educator.html", categories=categories)


# populate beerstyle dropdown - * Needs work(Dynamic Dropdown) *
@app.route("/beerstyle_names")
def beer_style():
    TABLENAME = "ba_beerstyles"
    query = f"SELECT DISTINCT Style FROM {TABLENAME}"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# populate beerstyle dropdown based upon Category input
@app.route("/beerstyle_filtered/<category>")
def beer_style_filtered(category):
    TABLENAME = "ba_beerstyles"
    query = f"SELECT Style FROM {TABLENAME} WHERE Category = '{category}'"
    df = pd.read_sql_query(query, sql_engine)
    df2 = pd.DataFrame({"Style": ["Select a Beer Style"]})
    df = df2.append(df)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# selector for beerstyle for gaugechart
@app.route("/beerstyle/<beerstyle>")
def guagechart(beerstyle):
    TABLENAME = "ba_beerstyles"
    query = f"SELECT * FROM {TABLENAME} WHERE Style = '{beerstyle}'"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# route to display top 5 beer recommendations
@app.route("/recommender/<beerstyle>")
def selector(beerstyle):
    TABLENAME1 = "top_5_beers"
    TABLENAME2 = "final_beers"
    query = f"select {TABLENAME2}.*, {TABLENAME1}.avg_rating, {TABLENAME1}.review_count from {TABLENAME2} cross join {TABLENAME1} on {TABLENAME1}.beer_id = {TABLENAME2}.beer_id where {TABLENAME1}.beer_style = '{beerstyle}'"
    df = pd.read_sql_query(query, sql_engine)
    isempty = df.empty
    if isempty == True:
        df2 = pd.DataFrame(
            {"beer_name": ["Sorry, we dont have a recommendation for that style"]}
        )
        df = df2.append(df)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# route to generate wordcloud for top beerstyles
@app.route("/category")
def top_beerstyles():
    TABLENAME = "final_beers"
    query = f"SELECT COUNT(beer_style) AS count, beer_style, category FROM {TABLENAME} GROUP BY beer_style, category"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# route to add beerstyle image
@app.route("/beerstyles_links/<beerstyle>")
def beer_style_links(beerstyle):
    TABLENAME = "beer_styles_links"
    query = f"SELECT * FROM {TABLENAME} WHERE beer_style = '{beerstyle}'"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# --------------------------------------------------------------#
#                       dashboard routes                       #
# --------------------------------------------------------------#


@app.route("/dashboard.html")
def dashboard():
    return render_template("dashboard.html")


@app.route("/state_data")
def state_data():
    TABLENAME = "us_state_data"
    query = f"SELECT * FROM {TABLENAME}"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


@app.route("/style_rank")
def style_rank():
    TABLENAME = "beer_style_pop"
    query = f"SELECT beer_style, review_count FROM {TABLENAME} ORDER BY review_count DESC LIMIT 10"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


@app.route("/category_data")
def category_data():
    TABLENAME = "ba_beerstyles"
    query = f"SELECT * FROM {TABLENAME}"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# state selector
@app.route("/statedata/<state>")
def state_stat(state):
    TABLENAME = "us_state_data"
    query = f"SELECT * FROM {TABLENAME} WHERE state = '{state}'"
    df = pd.read_sql_query(query, sql_engine)
    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# --------------------------------------------------------------#
#                       breweries routes                       #
# --------------------------------------------------------------#
@app.route("/breweries.html")
def breweries():
    return render_template("breweries.html")

# --------------------------------------------------------------#
#                       Recommender model routes                #
# --------------------------------------------------------------#

# Route returns the beer;brewery to populate the dropdown
@app.route("/knnrecommender.html")
def recommender_selector():
    beers = beers_df["beer_brewery"].tolist()
    beers.sort()
    beers.append("Choose a Beer")
    return render_template("knnrecommender.html", beers=beers)

# Beer_name is beer;brewery format to match the search route
@app.route("/neighbors/<beer_name>")  
def nearest_neighbors(beer_name):
    beer_raw_id = get_beer_raw_id(beer_name)
    df = get_beer_recc_df(beer_raw_id)
    df["score_mean"] = df["score_mean"].apply(lambda x: round(x, 2))

    # return json of the dataframe
    return Response(df.to_json(orient="records"), mimetype="application/json")


# Beer_name is beer;brewery format
@app.route("/predict", methods=["POST"])
def predict():
    data_dict = request.get_json()
    username = data_dict["username"]
    beer_name = data_dict["beer"]  
    beer_raw_id = get_beer_raw_id(beer_name)
    predict = algo_knn.predict(username, beer_raw_id)
    df_predict = pd.DataFrame(
        [predict], columns=["username", "beer_id", "r_ui", "prediction", "details"]
    )
    return Response(df_predict.to_json(orient="records"), mimetype="application/json")


# Route takes the username and returns the top10 and bottom 10 predicted ratings
@app.route("/userpredict/<username>")
def userpredict(username):
    beers = beers_df["beer_brewery"].tolist()
    predict_df = pd.DataFrame([])
    for beer in beers:
        beer_raw_id = get_beer_raw_id(beer)
        predict = algo_knn.predict(username, beer_raw_id)
        predict_df = predict_df.append(
            pd.DataFrame(
                [predict],
                columns=["username", "beer_id", "r_ui", "prediction", "details"],
            )
        )
    picks = pd.merge(predict_df, beers_df, on="beer_id")
    picks = picks.round({"prediction": 2, "score": 2})
    top_10picks = picks.sort_values(by=["prediction"], ascending=False)[:10]
    top_10picks["pick"] = "Top10"
    bot_10picks = picks.sort_values(by=["prediction"], ascending=False)[-10:]
    bot_10picks["pick"] = "Bottom10"
    user_picks = pd.concat([top_10picks, bot_10picks])
    return Response(user_picks.to_json(orient="records"), mimetype="application/json")


# Route will call /userpredict/<username> to render predictions for user with table
@app.route("/userpredict.html")
def predict_user_rating():
    return render_template("userpredict.html")


################################################################
#                           Main                               #
################################################################
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))

  
