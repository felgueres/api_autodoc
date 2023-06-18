# Eres un experto, te voy a dar un texto entre dos personas y quiero que respondes a la pregunta.
# Sigue estas instruccions 
# 1. Responde dando ejemplos tal cual aparecen
# 2. No añadas ni quites nada
# 3. Si no sabes la respuesta, responde con la pregunta y un string vacío

# Texto: {chunks}
# Pregunta: {question} 

standard_prompt = '''
Given passages and a dictionary key, extract from the text the value that corresponds to the key, then follow the instructions. 

Instructions:
1. Output a valid JSON that can be parsed by python json.loads
2. Output should be a string, not a list or dict.
3. Fill in exactly the same key, do not add or remove keys.
4. If the information is not present, respond with the key and an empty string. 
5. Only respond with the JSON, no commentary.

Passages: 173/2, BANDAPURA VILLAGE ROAD, BEHIND AVS CONCRETE OFF HOSUR ROAD, ANEKAL TALUKA, BENGALURU, BANGALORE KARNATAKA-562106
Key: address

Ouput:
{{"address": "173/2, BANDAPURA VILLAGE ROAD, BEHIND AVS CONCRETE OFF HOSUR ROAD, ANEKAL TALUKA, BENGALURU, BANGALORE KARNATAKA-562106"}}

Passages: Expenses incurred on treatment under Ayurveda, Unani, Sidha and Homeopathy systems of medicines in a Government Hospital or in any institute recognized by the government and/or accredited by the Quality Council of India/National Accreditation Board on Health up to 25% of the sum insured subject to a maximum of Rs. 25,000/- per policy period
Key: AYUSH treatment

Output:
{{"AYUSH treatment": "Expenses incurred on treatment under Ayurveda, Unani, Sidha and Homeopathy systems of medicines in a Government Hospital or in any institute recognized by the government and/or accredited by the Quality Council of India/National Accreditation Board on Health up to 25% of the sum insured subject to a maximum of Rs. 25,000/- per policy period"}}

Passages: {passages}
Key: {key}

Output:
'''

compare_prompt = '''Briefly analyze the similarity of the following two dictionaries, then conclude in the last line, "The similarity score is S", where S is an integer between 1 and 10.'''