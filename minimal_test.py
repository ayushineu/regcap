import streamlit as st

st.title("Minimal Test App")

st.write("This is a minimal test to verify Streamlit is working properly.")

user_input = st.text_input("Enter some text:", "explain what the file does")

st.write("You entered:", user_input)