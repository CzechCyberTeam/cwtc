require 'sinatra'
require "sinatra/json"
require "sinatra/cookies"
require "sinatra/reloader" if development?
require 'mongo'
require 'jwt'
require 'bcrypt'
require 'securerandom'
require "base64"
require 'fileutils'
require './utils.rb'


# hope you like ruby, sorry
# python was getting boring

client = Mongo::Client.new('mongodb://db:27017/progcodex')

configure do
    set :secret, 'B11MV6A5nLUGRKcPi4Q43uYyJ0kNGO'
    set :issuer, 'progcodex'
    set :motivation, './public/img/'
    set :uuid_regex, /[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}/
end

before do
    if request.body.size > 0 && request.media_type == "application/json"
        request.body.rewind
        @request_payload = JSON.parse request.body.read, symbolize_names: true
    end
end

def authenticated?(token)
    begin
        decoded_token = JWT.decode token, settings.secret, true, { algorithm: 'HS256' }

        claims = decoded_token.first

        raise 'Invalid issuer' unless claims['iss'] == settings.issuer

        raise 'An objection' unless claims['username']

        return claims['username'], claims['userid']
    rescue JWT::DecodeError => e
        return false
    rescue => e
        return false
    end
end

def new_token(username, id)
    exp = Time.now.to_i + 3 * 3600
    token_payload = {username: username, userid: id, exp: exp, iss: settings.issuer}

    token = JWT.encode token_payload, settings.secret, 'HS256'

    return token
end

before '/api/*' do
    unless ["/api/login", "/api/signup", "/api/motivation"].include?(request.path_info)
        halt 401, json("missing token cookie") unless cookies[:token]
        @session_username, @session_userid = authenticated?(cookies[:token])
        halt 401, json("invalid token") unless @session_username
    end
end

def generate_share_token(sub_id)
    return Base64.encode64(settings.secret^sub_id).gsub("\n", '')
end


not_found do
    json 'Looking for your lost youth?'
end
  

post '/api/login' do
    halt 400 unless @request_payload && @request_payload[:username] && @request_payload[:password] && @request_payload[:username].is_a?(String) && @request_payload[:password].is_a?(String)
    username = @request_payload[:username]
    password = @request_payload[:password]
    halt 400, json("username has to be between 8 and 25 characters") unless 8 <= username.length && 25 >= username.length
    halt 400, json("password has to be between 8 and 128 characters") unless 8 <= password.length && 128 >= password.length
    collection = client[:users]

    user = collection.find({ username: username }).limit(1).first
    halt 404, json("user not found") if user.nil?

    db_passwd = BCrypt::Password.new(user[:password])
    halt 401, json("wrong password") unless db_passwd == password
    # one can say that ruby programming is a true gem

    cookies[:token] = new_token(username, user[:_id])

    halt 202
end

post '/api/signup' do
    halt 400 unless @request_payload && @request_payload[:username] && @request_payload[:password] && @request_payload[:username].is_a?(String) && @request_payload[:password].is_a?(String)
    username = @request_payload[:username]
    password = @request_payload[:password]
    halt 400, json("username has to be between 8 and 25 characters") unless 8 <= username.length && 25 >= username.length
    halt 400, json("password has to be between 8 and 128 characters") unless 8 <= password.length && 128 >= password.length
    collection = client[:users]

    user = collection.find({ username: username }).limit(1).first
    halt 409, json("user already exists") unless user.nil?

    uuid = SecureRandom.uuid
    user_data = { _id: uuid, username: username, password: BCrypt::Password.create(password)}
    collection.insert_one(user_data)

    halt 201, json(:id => uuid)
end

delete '/api/logout' do
    cookies[:token] = 'gone' if cookies[:token]
    halt 204
end

get '/api/me' do
    json :username => @session_username
end

get '/api/motivation' do
    pictures_folder = settings.motivation
    picture_files = Dir.glob(File.join(pictures_folder, '*'))
    random_picture = picture_files.sample

    response.headers['Cache-Control'] = 'no-cache'
    send_file random_picture, type: 'image/jpeg'
end

get '/api/submissions' do
    collection = client[:submissions]

    mine = collection.find({ authorid: @session_userid })
    sharedwithme = collection.find({ sharedwith: { username: @session_username, id: @session_userid } })

    json({ :mine => mine.to_a, :sharedwithme => sharedwithme.to_a})
end

get '/api/submissions/stats' do
    collection = client[:submissions]

    query = params[:query]
    halt 400, json("invalid query") unless query && query.is_a?(String)

    begin
        query = JSON.parse query, symbolize_names: true
    rescue => e
        halt 400, json("invalid query")
    end

    statistics = collection.find(query)

    statistics = statistics.map { |stat| stat[:author] }.group_by { |author| author }.map { |author, authors| { author: author, count: authors.length } }

    json({ :statistics => statistics.to_a})
end

post '/api/submissions' do
    halt 400 unless @request_payload && @request_payload[:name] && @request_payload[:payload] && @request_payload[:name].is_a?(String) && @request_payload[:payload].is_a?(String)
    name = @request_payload[:name]
    payload = @request_payload[:payload]
    begin
        payload_decoded = Base64.strict_decode64(payload)
    rescue => e
        halt 400, json("invalid payload")
    end

    halt 413, json("too long") if payload_decoded.length > 250
    halt 400, json("empty name") if name.length < 1

    collection = client[:submissions]
    uuid = SecureRandom.uuid
    sharetoken = generate_share_token(uuid)

    FileUtils.mkdir_p './submissions/'+@session_userid

    File.open('./submissions/'+@session_userid+'/'+uuid, 'w') { 
        |file| file.write(payload_decoded) 
    }

    submission_data = { _id: uuid, name: name, authorid: @session_userid, author: @session_username, sharetoken: sharetoken, sharedwith: [], comments: []}

    collection.insert_one(submission_data)

    halt 201, json(:id => uuid)
end

get '/api/submissions/:submissionid' do
    uuid = params['submissionid']
    halt 400 unless uuid && uuid =~ settings.uuid_regex
    
    collection = client[:submissions]

    submission = collection.find({ _id: uuid.match(settings.uuid_regex)[0] }).limit(1).first

    payload = File.read('./submissions/'+submission[:authorid]+'/'+uuid)
    payload_encoded = Base64.encode64(payload)

    response = { :submission => submission, :payload => payload_encoded }
    
    halt json(response) if submission[:author] == @session_username || submission[:sharedwith].map{ |i| i[:username] }.include?(@session_username) || params['sharetoken'] || params['sharetoken'] == submission[:sharetoken]

    halt 401
end

put '/api/submissions/:submissionid' do
    uuid = params['submissionid']
    halt 400 unless uuid && uuid =~ settings.uuid_regex
    halt 400 unless @request_payload && @request_payload[:sharedwith] && @request_payload[:sharedwith].is_a?(Array)

    collection = client[:submissions]
    submission = collection.find({ _id: uuid.match(settings.uuid_regex)[0] }).limit(1).first

    halt 401 unless submission[:author] == @session_username

    sharedwith = Array.new()
    # iterate over the sharedwith array and get ids of the users from database
    for i in 0..@request_payload[:sharedwith].length-1
        user = client[:users].find({ username: @request_payload[:sharedwith][i] }).limit(1).first
        halt 400, json("user does not exist") if user.nil?
        sharedwith.push({ :username => user[:username], :id => user[:_id]})
    end

    result = collection.update_one({ _id: uuid }, { '$set' => { 'sharedwith' => sharedwith } } )

    json result.to_a
end

patch '/api/submissions/:submissionid' do
    uuid = params['submissionid']
    halt 400 unless uuid && uuid =~ settings.uuid_regex

    inputid = params[:inputid]
    halt 400, json("invalid inputid") unless inputid && inputid.is_a?(String) && inputid =~ /^[0-9]+$/

    collection = client[:submissions]
    submission = collection.find({ _id: uuid.match(settings.uuid_regex)[0] }).limit(1).first

    halt 401 unless submission[:author] == @session_username || submission[:sharedwith].map{ |i| i[:username] }.include?(@session_username) || params['sharetoken'] || params['sharetoken'] == submission[:sharetoken]

    output = `./sandbox/sbx ./submissions/#{submission[:authorid]}/#{uuid} #{inputid} 2>&1`

    json :output => output
end

post '/api/submissions/:submissionid/comments' do
    uuid = params['submissionid']
    halt 400 unless uuid && uuid =~ settings.uuid_regex
    halt 400 unless @request_payload && @request_payload[:comment] && @request_payload[:comment].is_a?(String)
    halt 413, json("too long") if @request_payload[:comment].length > 100

    collection = client[:submissions]
    submission = collection.find({ _id: uuid.match(settings.uuid_regex)[0] }).limit(1).first

    halt 401 unless submission[:author] == @session_username || submission[:sharedwith].map{ |i| i[:username] }.include?(@session_username) || params['sharetoken'] || params['sharetoken'] == submission[:sharetoken]

    result = collection.update_one({ _id: uuid }, { '$push' => { 'comments' => { 'author' => @session_username, 'comment' => @request_payload[:comment] } } } )

    json result.to_a
end

get '/*' do
    splat = params['splat'][0]
    erb :index, :locals => {:splat => splat}
end
