import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from azure.ai.translation.text import TextTranslationClient
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, ResultReason

# --- 1. CONFIGURATION ---
AZURE_LANGUAGE_KEY = "Your language key"
AZURE_LANGUAGE_ENDPOINT = "Your language endpoint"
AZURE_TRANSLATOR_KEY = "Your translator key"
AZURE_TRANSLATOR_REGION = "Your translator region"
AZURE_SPEECH_KEY = "Your speech key"
AZURE_SPEECH_REGION = "Your speech region"

# --- 2. CORE LOGIC FUNCTIONS ---

def summarize_text(text):
    client = TextAnalyticsClient(AZURE_LANGUAGE_ENDPOINT, AzureKeyCredential(AZURE_LANGUAGE_KEY))
    poller = client.begin_extract_summary([text])
    results = poller.result()
    summary = ""
    for result in results:
        if not result.is_error:
            summary = " ".join([s.text for s in result.sentences])
    return summary

def translate_text(text, target_lang):
    client = TextTranslationClient(credential=AzureKeyCredential(AZURE_TRANSLATOR_KEY), region=AZURE_TRANSLATOR_REGION)
    # Corrected parameters for the latest SDK
    response = client.translate(body=[text], to_language=[target_lang])
    return response[0].translations[0].text

from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, ResultReason, CancellationReason

def generate_audio_bytes(text, lang_code):
    # 1. Map short codes (fr, es) to full Locales (fr-FR, es-ES)
    # Azure Neural voices require the full locale string.
    locale_map = {
        "es": "es-ES",
        "fr": "fr-FR",
        "de": "de-DE",
        "hi": "hi-IN",
        "ja": "ja-JP",
        "en": "en-US",
        "zh-Hans": "zh-CN"
    }
    
    # Fallback to the code itself if not in map, or default to en-US
    full_locale = locale_map.get(lang_code, "en-US")

    speech_config = SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.speech_synthesis_language = full_locale
    
    # 2. Initialize synthesizer with no physical audio device (None)
    synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    # 3. Synchronous wait with .get()
    result = synthesizer.speak_text_async(text).get()

    if result.reason == ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    
    # 4. CRITICAL: Capture and Print the exact error if it fails
    elif result.reason == ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
            # This will show up in your terminal where you ran 'streamlit run'
            
    return None
# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Intelligent News AI", layout="wide")
st.title("📰 Intelligent News Summarizer")

# Use columns for a clean layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input Article")
    news_input = st.text_area("Paste the full news article here:", height=300)
    
    # Language dictionary for the dropdown
    lang_options = {"Spanish": "es", "French": "fr", "German": "de", "Hindi": "hi", "Japanese": "ja"}
    selected_lang_name = st.selectbox("Translate to:", list(lang_options.keys()))
    target_lang = lang_options[selected_lang_name]

    if st.button("Summarize & Translate", use_container_width=True):
        if news_input.strip():
            with st.spinner("Processing..."):
                # Run AI services
                summary = summarize_text(news_input)
                translated = translate_text(summary, target_lang)
                
                # Save results to session state so they persist during re-runs
                st.session_state.result_text = translated
                st.session_state.current_lang = target_lang
        else:
            st.warning("Please enter some text first.")

with col2:
    st.subheader("AI Result")
    if 'result_text' in st.session_state:
        st.info(f"Summary in {selected_lang_name}:")
        st.write(st.session_state.result_text)
        
        st.divider()
        
        # Audio Section
        if st.button("🔊 Generate Audio Speech", use_container_width=True):
            with st.spinner("Synthesizing voice..."):
                audio_bytes = generate_audio_bytes(st.session_state.result_text, st.session_state.current_lang)
                if audio_bytes:
                    # This displays the player and allows the user to play/pause/download
                    st.audio(audio_bytes, format='audio/wav')
                else:
                    st.error("Could not generate audio. Check your Azure Speech credentials.")
    else:
        st.write("Your summary will appear here.")