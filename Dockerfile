FROM python:3.11-slim
WORKDIR /app
RUN apt update && apt install -y \
    ffmpeg \
    pulseaudio \
    redis-server \
    pulseaudio-utils \
    libpulse0 \
    libpulse-dev \
    alsa-utils \
    libasound2 \
    libasound2-plugins \
    locales \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


RUN echo "pcm.!default { \n\
    type pulse \n\
    fallback 'sysdefault' \n\
    hint {\n\
    show on \n\
    description 'Default Audio Device (PulseAudio)' \n\
    } \n\
    }\n\
    ctl.!default {\n\
    type pulse \n\
    }" >/etc/asound.conf    

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen

RUN useradd -m -u 1000 -s /bin/bash audiobot 

USER root
RUN mkdir -p /var/run/user/1000/pulse && \
    chown -R audiobot:audiobot /app /var/run/user/1000

COPY requirements.txt .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

# RUN playwright install chromium chromium-headless-shell
RUN playwright install chrome --with-deps

COPY start.sh .

RUN chown -R audiobot:audiobot /app

RUN chmod +x start.sh
RUN chown audiobot:audiobot start.sh

USER audiobot

ENV PULSE_SERVER=unix:/var/run/user/1000/pulse/native
ENV XDG_RUNTIME_DIR=/var/run/user/1000
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PYTHONUNBUFFERED=1

CMD [ "./start.sh" ]