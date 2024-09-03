# Use the official Ruby image as the base
FROM ruby@sha256:05ca729e257fc550f4228714a5f6c9f377d4dab92c30b2213340ddb7eec0b597

# Set the working directory in the container
WORKDIR /app

# Copy the Gemfile and Gemfile.lock to the working directory
COPY Gemfile Gemfile.lock ./

# Install dependencies using Bundler
RUN gem install bundler && bundle install --jobs 20 --retry 5

# install build dependencies for cpp
RUN apt-get update && apt-get install -y build-essential make

# Copy the rest of the application code to the working directory
COPY . .

WORKDIR /app/sandbox

RUN make

# Expose port 4567 (the default Sinatra port)
EXPOSE 4567

ENV RACK_ENV=production

WORKDIR /app
# Set the command to start the application
CMD ["ruby", "main.rb"]
#CMD ["bash", "-c", "RACK_ENV=production ruby app.rb"]
