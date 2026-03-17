import dash
from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# importation de la base 
df = pd.read_csv("datasets/data.csv")

# nettoyage des colonnes 
numeric_cols = ["Quantity", "Avg_Price", "Discount_pct", "Offline_Spend", "Online_Spend", "Delivery_Charges", "GST"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# harmonisation de la date
df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"], errors="coerce")
df["Date"] = df["Transaction_Date"]

# supprimer les dates manquantes
df = df.dropna(subset=["Date"])

# CA avec remise
df["Sales"] = df["Quantity"] * df["Avg_Price"] * (1 - df["Discount_pct"] / 100)

# Mois
df["Month"] = df["Date"].dt.to_period("M")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

app.layout = dbc.Container([

    # titre avec fond rose et le filtre de zone
dbc.Row([
    dbc.Col(
        html.Div([
            dbc.Row([
                dbc.Col(
                    html.H2("ECAP Store — Tableau de bord",
                            style={"margin": "0", "padding": "10px 0"}),
                    md=8
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="zone-filter",
                        options=[{"label": loc, "value": loc}
                                 for loc in sorted(df["Location"].dropna().astype(str).unique())],
                        value=None,
                        placeholder="Choisir une zone",
                        clearable=True,
                        style={"height": "45px", "fontSize": "16px"}
                    ),
                    md=4
                )
            ])
        ],
        style={
            "backgroundColor": "#F8D7E3",
            "height": "60px",
            "borderRadius": "8px",
            "marginTop": "10px",
            "marginBottom": "10px",
            "padding": "10px"
        }),
        md=12
    )
]),

    dbc.Row([
        dbc.Col([

            # KPI
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id="kpi-ca", config={"displayModeBar": False})
                        ])
                    ),
                    md=6
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id="kpi-units", config={"displayModeBar": False})
                        ])
                    ),
                    md=6
                ),
            ], className="mb-3"),

            # Bar chart
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id="bar-chart", style={"height": "350px"})
                        ])
                    ),
                    md=12
                )
            ])

        ], md=5),

        # colonne à droite
        dbc.Col([

            # Line chart
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(id="line-chart", style={"height": "380px"})
                        ])
                    ),
                    md=12
                )
            ], className="mb-3"),

            # Tableau
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H5("Table des 100 dernières ventes"),
                            dash_table.DataTable(
                                id="sales-table",
                                page_size=10,
                                style_table={
                                    "maxHeight": "250px",
                                    "overflowY": "scroll",
                                    "overflowX": "auto"
                                },
                                style_cell={"padding": "5px", "fontSize": "13px"},
                                style_header={"fontWeight": "bold", "backgroundColor": "#f0f0f0"}
                            )
                        ])
                    ),
                    md=12
                )
            ])

        ], md=7)

    ])

], fluid=True)


# les callback
@app.callback(
    Output("kpi-ca", "figure"),
    Output("kpi-units", "figure"),
    Output("bar-chart", "figure"),
    Output("line-chart", "figure"),
    Output("sales-table", "data"),
    Input("zone-filter", "value")
)
def update_dashboard(selected_zone):

    # filtre pour les zones
    dff = df.copy()
    if selected_zone:
        dff = dff[dff["Location"] == selected_zone]

    # KPI
    dec = dff[dff["Month"] == "2019-12"]
    nov = dff[dff["Month"] == "2019-11"]

    dec_sales = dec["Sales"].sum()
    nov_sales = nov["Sales"].sum()

    dec_units = dec["Quantity"].sum()
    nov_units = nov["Quantity"].sum()

    # KPI CA
    fig_ca = go.Figure()
    fig_ca.add_trace(go.Indicator(
        mode="number+delta",
        value=dec_sales,
        number={"valueformat": ",.0f", "font": {"size": 26}},
        title={"text": "Chiffre d'affaires (Décembre)", "font": {"size": 12}},
        delta={"reference": nov_sales, "relative": False, "font": {"size": 12}},
    ))
    fig_ca.update_layout(height=90, margin=dict(l=10, r=10, t=20, b=0))

    # KPI unités vendues
    fig_units = go.Figure()
    fig_units.add_trace(go.Indicator(
        mode="number+delta",
        value=dec_units,
        number={"valueformat": ",.0f", "font": {"size": 26}},
        title={"text": "Unités vendues (Décembre)", "font": {"size": 12}},
        delta={"reference": nov_units, "relative": False, "font": {"size": 12}},
    ))
    fig_units.update_layout(height=90, margin=dict(l=10, r=10, t=20, b=0))

    # top 10 catégories triées décroissant par nombre de ventes

    cat_sex = dff.groupby(["Product_Category", "Gender"])["Sales"].sum().reset_index()
    top10 = cat_sex.groupby("Product_Category")["Sales"].sum().nlargest(10).index
    filtered = cat_sex[cat_sex["Product_Category"].isin(top10)]

    bar_chart = px.bar(
        filtered.sort_values("Sales", ascending=False),
        x="Sales",
        y="Product_Category",
        color="Gender",
        barmode="group",
        orientation="h",
        title="Top 10 des meilleures ventes",
        color_discrete_map={"F": "deeppink", "M": "steelblue"},
        template="plotly_white"
    )
    # améliorer la lisibilité
    bar_chart.update_layout(
        margin=dict(l=80, r=20, t=40, b=20),
        yaxis={'categoryorder': 'total ascending'}
    )   

    # pour pas que les dates encombrent le graphique 
    dff["Week"] = dff["Date"].dt.to_period("W").apply(lambda r: r.start_time)
    weekly = dff.groupby("Week")["Sales"].sum().reset_index()

    line_chart = px.line(
        weekly,
        x="Week",
        y="Sales",
        title="Évolution du chiffre d'affaires par semaine",
        template="plotly_white"
    )

    line_chart.update_layout(height=380)
    line_chart.update_xaxes(tickformat="%d %b %Y", nticks=10, tickangle=0)
    line_chart.update_yaxes(range=[0, weekly["Sales"].max() * 1.15])

    # tableau de données
    table_data = dff.sort_values("Date", ascending=False).head(100)[[
        "Date", "Gender", "Location", "Product_Category",
        "Quantity", "Avg_Price", "Discount_pct"
    ]].to_dict("records")

    return fig_ca, fig_units, bar_chart, line_chart, table_data


if __name__ == "__main__":
    app.run(debug=True, port=8056, jupyter_mode="external")