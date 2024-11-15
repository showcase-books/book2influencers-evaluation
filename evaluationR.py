import streamlit as st
import pandas as pd
import requests
import io


# Set up page configuration with "wide" layout
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# File path to save the recommendation states
# save_file_path = "/Users/maxencebrochard/Documents/showcase/code/experiments/book2influencers/evaluation/data/20241104_classic_books.pkl"
save_file_path = "data/20241104_classic_books.pkl"


# Load data once into session state
def load_data():
    df = pd.read_pickle(save_file_path)
    st.session_state.df = df

    # influencer_df = pd.read_pickle("data/20241023_influencer_with_embeddings.pkl")

    # Public URL of your GCS file
    file_url = "https://storage.googleapis.com/book2influencers-evaluation/20241023_influencer_with_embeddings.pkl"

    # Download the file
    response = requests.get(file_url)
    response.raise_for_status()  # Raise an error if the request fails

    # Load the data into a DataFrame
    influencer_df = pd.read_pickle(io.BytesIO(response.content))

    influencer_df = influencer_df[
        [
            "account_name",
            "fullName",
            "inputUrl",
            "businessCategoryName",
            "followersCount",
            "biography",
            "additional_content",
        ]
    ]

    st.session_state.influencer_df = influencer_df


# Initialize session state variables
def initialize_state():
    if "initialization_done" not in st.session_state:
        st.session_state.initialization_done = True
        st.session_state.book_index = 0
        st.session_state.lcc1_options = sorted(
            st.session_state.df["LCC_1"].dropna().unique()
        )
        st.session_state.lcc1_filter = st.session_state.lcc1_options[0]
        # st.session_state.recommendation_states = {}


# Load or initialize checkbox states for the current book's recommendations
def load_checkbox_states(book_data):

    local_checkbox_states = {}

    # Display each recommendation with a checkbox and additional information
    for reco in book_data["recommendations"]:
        correct_key = f"correct_{reco['rank']}"
        is_checked = st.checkbox(
            f"Rank {reco['rank']}: {reco['account_name']} (Score: {reco['score']:.2f})",
        )
        local_checkbox_states[correct_key] = is_checked

    return local_checkbox_states


# Save checkbox states for the current book's recommendations and update df before saving
def save_checkbox_states(local_states):
    current_book_id = st.session_state.df.iloc[st.session_state.book_index]["id"]
    book_row_index = st.session_state.df[
        st.session_state.df["id"] == current_book_id
    ].index[0]

    # Extract recommendations
    current_recommendations = st.session_state.df.loc[book_row_index, "recommendation"]

    # Update the 'correct_reco' field based on the checkbox states in local_states
    for reco in current_recommendations:
        reco["correct_reco"] = local_states.get(f"correct_{reco['rank']}", False)

    # Directly assign the updated list back to the exact row in st.session_state.df
    st.session_state.df.at[book_row_index, "recommendation"] = current_recommendations

    # Save the updated dataframe to the file
    st.session_state.df.to_pickle(save_file_path)
    st.success("Changes saved successfully!")


# Fetch book data and recommendations for the current book
def get_book_data():
    book = st.session_state.df.iloc[st.session_state.book_index]

    recommendations = [
        st.session_state.df.loc[
            st.session_state.df["id"] == book["id"], "recommendation"
        ].values[0][:10]
    ]

    recommendations = (
        recommendations[0]
        if len(recommendations) > 0 and isinstance(recommendations[0], list)
        else []
    )

    for reco in recommendations:
        reco.setdefault("correct_reco", False)
        detail_reco = st.session_state.influencer_df[
            st.session_state.influencer_df.account_name == reco["account_name"]
        ]
        reco["link"] = detail_reco["inputUrl"].values[0]
        reco["business_category"] = detail_reco["businessCategoryName"].values[0]
        reco["followers_count"] = detail_reco["followersCount"].values[0]
        reco["biography"] = detail_reco["biography"].values[0]
        reco["additional_content"] = detail_reco["additional_content"].values[0]
    return {
        "title": book["title"],
        "image_url": f"https://www.gutenberg.org/cache/epub/{book['id']}/pg{book['id']}.cover.medium.jpg",
        "author": book["author"],
        "subjects": book["subjects"],
        "LCC_1": book.get("LCC_1", "N/A"),
        "LCC_2": book.get("LCC_2", "N/A"),
        "description": book.get("description", "No description available"),
        "recommendations": recommendations,
    }


def update_index(increment):
    st.session_state.book_index = (st.session_state.book_index + increment) % len(
        st.session_state.df
    )


# Main execution
if "initialization_done" not in st.session_state:
    load_data()
    initialize_state()

# Retrieve book data and checkbox states after updating index
book_data = get_book_data()
current_book_id = st.session_state.df.iloc[st.session_state.book_index]["id"]

# if "local_checkbox_states" not in st.session_state:  # initialization of current recos
#     st.session_state.local_checkbox_states = load_checkbox_states(book_data)

# Display navigation buttons at the top of the page
col_prev, col_next = st.columns([1, 1])
if col_prev.button("Previous"):
    update_index(-1)
    st.rerun()

if col_next.button("Next"):
    update_index(1)
    st.rerun()

# Layout with two wider columns: left (book info) and right (checkboxes)
col1, col2 = st.columns([4, 2])

with col1:
    # Display book title at the top
    st.markdown(
        f"<h1 style='text-align: center;'>{book_data['title']}</h1>",
        unsafe_allow_html=True,
    )

    # Create two columns inside col1 for the image and description with spacing
    img_col, desc_col = st.columns([1, 2])

    with img_col:
        st.write("")  # Adds vertical spacing
        st.image(book_data["image_url"], width=300, caption=book_data["title"])
        st.write("")  # Adds vertical spacing after image

    with desc_col:
        st.write(f"**Author:** {book_data['author']}")
        st.write(
            f"**Subjects:** {', '.join(book_data['subjects']) if isinstance(book_data['subjects'], set) else 'N/A'}"
        )
        st.write(f"**LCC_1:** {book_data['LCC_1']}")
        st.write(f"**LCC_2:** {book_data['LCC_2']}")
        st.write(f"**Description:** {book_data['description']}")

# Display recommendations with checkboxes and additional information in the right column
with col2:
    st.markdown("### Recommendations")
    with st.form("reco_form"):
        # Initialize local_checkbox_states for the current book
        local_checkbox_states = {}

        # Display each recommendation with a checkbox and additional information
        for reco in book_data["recommendations"]:
            correct_key = f"correct_{reco['rank']}"
            is_checked = st.checkbox(
                f"Rank {reco['rank']}: {reco['account_name']} (Score: {reco['score']:.2f})",
                value=reco.get("correct_reco", False),
            )
            local_checkbox_states[correct_key] = is_checked

            # Display additional information
            st.markdown(
                f"**Profile Link**: [View Profile]({reco['link']})",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Business Category**: {reco['business_category']}")
            st.markdown(f"**Followers Count**: {reco['followers_count']}")
            st.markdown(f"**Biography**: {reco['biography']}")
            with st.expander("Show Additional Content"):
                st.markdown(reco["additional_content"], unsafe_allow_html=True)

        # st.session_state.local_checkbox_states = local_checkbox_states

        # Place the "Save Changes" button at the top and save updated states
        if st.form_submit_button("Save Changes"):
            save_checkbox_states(local_checkbox_states)
