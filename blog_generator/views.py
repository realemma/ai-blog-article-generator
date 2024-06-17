from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate ,login,logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.conf import settings
from pytube import YouTube
import os
import openai
import assemblyai as aai
from .models import BlogPost

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error':'Invalid data sent'}, status=400)
        
        # get yt title
        title = yt_title(yt_link)
        #get transcipt
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error':"Failed to get transcript"}, status=500)

        #use openAI to generate  the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error':"Failed to get transcript"}, status=500)
        # save blog article to database
        new_blog_article=BlogPost.objects.create(
            user = request.user,
            youtube_title = title ,
            youtube_link= yt_link,
            generated_content= blog_content,
        )

        new_blog_article.save()

        #return blog article as a response
        return JsonResponse({'content':blog_content})
    else:
        return JsonResponse ({'error': 'Invalid request methos'}, status=405)


def generate_blog_from_transcription(transcription):
    openai.api_key = "sk-proj-h9VD0vE6wYAycDtPW3WxT3BlbkFJbmwOH4rJ8oz3WHLMauNo"

    prompt = f"Based on the following transcript from a YouTube video,write a comprehensive blog article, write it based on the transcript, but dont make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1000
    )

    generated_content = response.choices[0].text.strip()

    return generated_content


def download_audio(link):
    yt= YouTube(link)
    video=yt.streams.filter(only_audio=True).first()
    out_file=video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    #audio_file = pass
    aai.settings.api_key = "853951312e5742e7b0d7a5e5e0f6f61a"

    transcriber= aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text


def blog_list(request):
    blog_articles= BlogPost.objects.filter(user=request.user)
    return render(request,'all-blogs.html',{'blog_articles':blog_articles})

def blog_details(request, pk):
    blog_article_detail= BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')
    

def user_login(request):
    if request.method == 'POST':
        username= request.POST['username']
        password=request.POST['password']
        user=authenticate(username=username,password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message':error_message} )
    return render(request,'login.html')



def user_signup(request):
    if request.method == "POST" :
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatpassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'password do not match'
            return render(request, 'signup.html', {'error_message':error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')