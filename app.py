import os
import time
import threading
import schedule
import random
from flask import Flask, request, render_template
from instagrapi import Client
from moviepy.editor import VideoFileClip

app = Flask(__name__)

# सेटिंग्स
UPLOAD_FOLDER = '/tmp'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ग्लोबल डाटा
job_data = {
    "original_video_path": None, # असली वीडियो यहाँ सेव रहेगा
    "caption": "",
    "username": "",
    "password": "",
    "is_running": False
}

def make_video_unique(input_path):
    """
    यह फंक्शन वीडियो का DNA (Hash) बदल देगा
    ताकि Instagram उसे स्पैम न समझे।
    """
    try:
        output_path = input_path.replace(".mp4", "_unique.mp4")
        
        # वीडियो लोड करें
        clip = VideoFileClip(input_path)
        
        # वीडियो के अंत से 0.1 से 0.3 सेकंड के बीच का कोई रैंडम हिस्सा काट दें
        # इससे वीडियो इंसान को सेम दिखेगी, पर फाइल अलग बन जाएगी
        random_cut = random.uniform(0.1, 0.3)
        new_duration = clip.duration - random_cut
        
        # नई क्लिप बनाएं
        new_clip = clip.subclip(0, new_duration)
        
        # इसे सेव करें (Low quality preset ताकी जल्दी हो जाए)
        new_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", temp_audiofile='/tmp/temp-audio.m4a', remove_temp=True, fps=24, preset='ultrafast')
        
        # मेमोरी खाली करें
        clip.close()
        new_clip.close()
        
        return output_path
    except Exception as e:
        print(f"Error making video unique: {e}")
        return input_path # अगर एरर आए तो ओरिजिनल ही भेज दें

def instagram_upload_job():
    print("Task Started: Preparing video...")
    if job_data["original_video_path"] and job_data["username"]:
        try:
            # 1. वीडियो को यूनिक बनाएं (जुगाड़)
            unique_video = make_video_unique(job_data["original_video_path"])
            
            # 2. लॉगिन करें
            cl = Client()
            cl.login(job_data["username"], job_data["password"])
            
            # 3. अपलोड करें
            print("Uploading unique video...")
            cl.video_upload(
                unique_video,
                caption=job_data["caption"]
            )
            print("Video Uploaded Successfully!")
            
            # 4. जो यूनिक फाइल बनाई थी उसे डिलीट कर दें (स्पेस बचाने के लिए)
            if unique_video != job_data["original_video_path"]:
                os.remove(unique_video)
                
        except Exception as e:
            print(f"Error uploading: {e}")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(10)

# थ्रेड स्टार्टर
if not job_data["is_running"]:
    # रोज सुबह 10 बजे अपलोड (आप टाइम बदल सकते हैं)
    schedule.every().day.at("10:00").do(instagram_upload_job)
    
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()
    job_data["is_running"] = True

@app.route('/', methods=['GET', 'POST'])
def index():
    message = "Server is Running..."
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashtags = request.form.get('hashtags')
        video_file = request.files['video']

        if video_file:
            # ओरिजिनल वीडियो को 'source.mp4' के नाम से सेव करें
            filepath = os.path.join(UPLOAD_FOLDER, "source.mp4")
            video_file.save(filepath)
            
            job_data["username"] = username
            job_data["password"] = password
            job_data["caption"] = f"{hashtags} #DailyPost"
            job_data["original_video_path"] = filepath
            
            message = "Video Saved! The system will now edit it slightly and upload it daily."

    return render_template('index.html', message=message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
      
