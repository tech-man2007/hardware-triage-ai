import streamlit as st
import json
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# --- 1. FUZZY LOGIC SYSTEM ---
# Fuzzification: Define inputs (temperature, battery drain) and output (risk)
temp = ctrl.Antecedent(np.arange(0, 101, 1), 'temperature')
drain = ctrl.Antecedent(np.arange(0, 101, 1), 'drain')
risk = ctrl.Consequent(np.arange(0, 101, 1), 'risk')

# Membership functions
temp['normal'] = fuzz.trimf(temp.universe, [0, 0, 50])
temp['warm'] = fuzz.trimf(temp.universe, [30, 50, 70])
temp['critical'] = fuzz.trimf(temp.universe, [60, 100, 100])

drain['slow'] = fuzz.trimf(drain.universe, [0, 0, 40])
drain['moderate'] = fuzz.trimf(drain.universe, [30, 50, 70])
drain['fast'] = fuzz.trimf(drain.universe, [60, 100, 100])

risk['low'] = fuzz.trimf(risk.universe, [0, 0, 40])
risk['moderate'] = fuzz.trimf(risk.universe, [30, 50, 70])
risk['high'] = fuzz.trimf(risk.universe, [60, 100, 100])

# Rule Evaluation
rule1 = ctrl.Rule(temp['normal'] & drain['slow'], risk['low'])
rule2 = ctrl.Rule(temp['warm'] | drain['moderate'], risk['moderate'])
rule3 = ctrl.Rule(temp['critical'] & drain['fast'], risk['high'])

risk_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
risk_sim = ctrl.ControlSystemSimulation(risk_ctrl)

# --- 2. STREAMLIT UI & LANGCHAIN ---
st.title("📱 Hardware Triage & Health Analyzer")
st.write("Describe your device's symptoms (e.g., 'My phone gets super hot when gaming and the battery dies in an hour').")


symptoms = st.text_area("Device Symptoms:")

if st.button("Analyze Hardware") and symptoms:
    try:
        # LangChain Reasoning: Extract numerical inputs from free text
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        prompt = PromptTemplate(
            input_variables=["symptoms"],
            template="Analyze the following hardware symptoms. Estimate the device's temperature severity (0-100) and battery drain severity (0-100). Return ONLY a valid JSON object with keys 'temperature' and 'drain'. Symptoms: {symptoms}"
        )
        chain = prompt | llm
        
        response = chain.invoke({"symptoms": symptoms})
        
        # Clean JSON from markdown blocks if necessary
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        extracted_data = json.loads(clean_json)
        
        st.write("### LangChain Extraction")
        st.json(extracted_data)
        
        # Defuzzification: Calculate final risk score
        risk_sim.input['temperature'] = extracted_data['temperature']
        risk_sim.input['drain'] = extracted_data['drain']
        risk_sim.compute()
        
        final_score = risk_sim.output['risk']
        st.write(f"### Fuzzy Logic Risk Score: **{final_score:.2f} / 100**")
        
        # Hardware Action Plan based on output
        st.write("### Recommended Action")
        if final_score > 75:
            st.error("Severe Degradation: The motherboard or battery is failing. A manual battery boost via direct terminal wires or a deep motherboard diagnostic is highly recommended before the device bricks.")
        elif final_score > 50:
            st.warning("Moderate Degradation: Check for CPU throttling. You may need to apply fresh thermal pads or investigate if a faulty proximity sensor is keeping the screen active and causing idle drain.")
        else:
            st.success("Stable: Hardware is functioning normally. Consider flashing a lightweight custom ROM if you want to optimize battery retention further.")

    except Exception as e:
        st.error(f"Error during processing: {e}")
