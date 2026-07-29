User clicks a central upload button -> Document preview + a text box asking the user to put any additional information -> Analyses of the doc -> Should it be processed as an OCR doc or a normal printed PDF doc

If OCR, use a methodology to process it like OCR -> provide the data to an AI model -> create core memory -> store data points in DB
If printed PDF doc, pass the data to an AI model -> extract data points -> store PDF in storage -> create core memory -> store data points in DB

Open Questions:
- how do core memories play a part in the overall answers, actions, reminders being supplied by the chatbot?
- how do we upload data?
- how do we extract date, clinic name, doctor name, and automatically categorize with the help of tags?
- how do we design the API