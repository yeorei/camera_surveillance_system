from django.shortcuts import render, redirect
from django.http.response import StreamingHttpResponse
from .camera import VideoCamera
from .forms import UserForm
from .models import *
import os, ffmpeg

def index(request):
	form = UserForm()
	if request.method == 'POST':
		form = UserForm(request.POST)
		if form.is_valid():
			form.save()
			return redirect(camera_view)
	return render(request, 'index.html', {'form': form})

def camera_view(request):
	user_info = UserProfile.objects.latest('id')
	return render(request, 'camera_view.html', {'user_info': user_info})

def update_alert(request):
	user_info = UserProfile.objects.latest('id')
	user_info.alert_on = not user_info.alert_on
	user_info.save()
	return redirect('camera_view')

def recordings(request):
	all_recordings = Recording.objects.all()
	for recording in all_recordings:
		if str(recording.file).endswith('.avi'):
			filename = os.path.splitext(str(recording.file))[0]
			stream = ffmpeg.input(str(recording.file)).output(filename+'.mp4', vcodec= 'h264')
			ffmpeg.run(stream, overwrite_output = True)
			recording.file = filename+'.mp4'
			recording.save()
	return render(request, 'recordings.html', {'recording': all_recordings})

def delete_recording(request, id):
	recording = Recording.objects.get(id=id)
	recording.delete()
	return redirect('recordings')

def edit_account(request):
	form = UserForm()
	if request.method == 'POST':
		form = UserForm(request.POST)
		if form.is_valid():
			form.save()
			return redirect(camera_view)
	return render(request, 'edit_account.html', {'form': form})

def gen(camera):
	while True:
		frame = camera.get_frame()
		yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def video_feed(request):
	return StreamingHttpResponse(gen(VideoCamera()), content_type='multipart/x-mixed-replace; boundary=frame')