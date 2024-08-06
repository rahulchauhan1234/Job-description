import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login as auth_login
from .models import TokenUsage
import google.generativeai as genai
from dotenv import load_dotenv
from time import time

GEMINI_API_KEY = "AIzaSyBQw-vnSAUrMHoqbDWjWIiHTKpJxIvMVt0"
genai.configure(api_key=GEMINI_API_KEY)

# Estimate token count (assuming roughly 4 characters per token)
def estimate_tokens(text):
    return len(text) // 4

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('generate')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def calculate_cost(input_tokens, output_tokens):
    cost_input_short = 0.35 / 1_000_000
    cost_input_long = 0.70 / 1_000_000
    cost_output_short = 1.05 / 1_000_000
    cost_output_long = 2.10 / 1_000_000

    if input_tokens <= 128_000:
        input_cost = input_tokens * cost_input_short
        output_cost = output_tokens * cost_output_short
    else:
        input_cost = input_tokens * cost_input_long
        output_cost = output_tokens * cost_output_long
    
    total_cost = input_cost + output_cost
    return total_cost

def rate_limit_user(user_id, limit=5, timeout=60):
    key = f'rate_limit:{user_id}'
    request_times = cache.get(key, [])

    current_time = time()

    request_times = [timestamp for timestamp in request_times if current_time - timestamp < timeout]

    if len(request_times) >= limit:
        return False

    request_times.append(current_time)
    cache.set(key, request_times, timeout=timeout)
    return True

@login_required
def generate_view(request):
    if request.method == 'POST':
        user_id = request.user.id

        if not rate_limit_user(user_id):
            return render(request, 'generate.html', {'error': 'Rate limit exceeded. Please wait a minute before trying again.'})

        job_title = request.POST.get('job_title')
        prompt = f'''Description of {job_title} only nothing else describe what company wants make it in paragraph according to positions, 
        also add responsibility and qualification in bullet. Do not include the job title as heading.'''

        try:
            model = genai.GenerativeModel(
                'gemini-1.5-flash',
                generation_config=genai.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.9,
                ))
            
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.1,
                )
            )

            # Check if response contains a valid `Part`
            if not response or not hasattr(response, 'text') or not response.text:
                raise ValueError('No valid response was generated.')

            job_description = response.text

        except ValueError as e:
            return render(request, 'generate.html', {'error': str(e)})

        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(job_description)
        total_tokens = input_tokens + output_tokens
        cost = calculate_cost(input_tokens, output_tokens)

        formatted_description = f"<h2>{job_title}</h2><div class='job-details'>" + job_description.replace(
            '**Responsibilities:**',
            '<b>Responsibilities:</b><ul>'
        ).replace(
            '**Qualifications:**',
            '</ul><b>Qualifications:</b><ul>'
        ).replace(
            '* ',
            '<li>'
        ).replace(
            '\n',
            '</li>'
        ) + '</ul></div>'

        TokenUsage.objects.create(
            user=request.user,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost
        )

        return render(request, 'generate.html', {'job_description': formatted_description, 'total_tokens': total_tokens, 'cost': cost})
    
    return render(request, 'generate.html')
