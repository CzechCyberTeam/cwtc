const apiURL = location.protocol + '//' + location.host + "/api/"

class API {
    constructor(baseUri) {
        this.baseUri = baseUri
    }
    get(url) {
        const requestOptions = {
            method: 'GET'
        };
        return fetch(this.baseUri+url, requestOptions).then(this.handleResponse);
    }
    
    post(url, body={}) {
        const requestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        };
        return fetch(this.baseUri+url, requestOptions).then(this.handleResponse);
    }

    patch(url, body={}) {
        const requestOptions = {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        };
        return fetch(this.baseUri+url, requestOptions).then(this.handleResponse);
    }

    put(url, body={}) {
        const requestOptions = {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        };
        return fetch(this.baseUri+url, requestOptions).then(this.handleResponse);
    }

    delete(url) {
        const requestOptions = {
            method: 'DELETE'
        };
        return fetch(this.baseUri+url, requestOptions).then(this.handleResponse);
    }
    
    handleResponse(response) {
        return response.text().then(text => {
            const data = text && JSON.parse(text);
            
            if (!response.ok) {
                const error = "Error: "+data || response.statusText;
                return Promise.reject(error);
            }
    
            return data;
        });
    }
}

class Progcodex {
    constructor(api) {
        this.api = api
    }
    login(username, password) {
        return this.api.post("login",{username: username, password:password})
    }
    signup(username, password) {
        return this.api.post("signup",{username: username, password:password})
    }
    logout() {
        return this.api.delete("logout")
    }
    me() {
        return this.api.get("me")
    }
    submissions() {
        return this.api.get("submissions")
    }
    addSubmission(name, program) {
        return this.api.post("submissions",{name: name, payload:program})
    }
    getSubmission(uuid, sharetoken="") {
        // TODO: sharetokens
        return this.api.get("submissions/"+uuid)
    }
    stats(filter={}) {
        return this.api.get("submissions/stats?query="+JSON.stringify(filter))
    }
    shareSubmission(uuid, sharedwith=[]) {
        return this.api.put("submissions/"+uuid,{sharedwith: sharedwith})
    }
    executeSubmission(uuid, inputid="0") {
        return this.api.patch("submissions/"+uuid+"?inputid="+inputid)
    }
    addComment(uuid, comment) {
        return this.api.post("submissions/"+uuid+"/comments", {comment: comment})
    }
}

let api = new API(apiURL)
var progcodex = new Progcodex(api)

const router = new Navigo('/');

router.on('/', function () {
    document.getElementById('app').innerHTML = `
    <div class="content">
    <h1 class="title">Welcome to ProgCodex</h1>
    <p>Your new worst student nightmare</p>
    <figure class="image" id="img">
    </figure>
    <p class="mt-6">
    <b>WARNING FOR STUDENTS: This website is for doing serious work!!! If your uploaded homework will do anything except reading the provided input file descriptor, doing some <i>computation</i> and outputting the output to stdout, you will be banned from the website. If you upload a virus, you will be banned from the website. If you upload a virus that spreads to other users, you will be banned from the website and reported to the authorities. If you upload a virus that spreads to other users and causes damage, you will be banned from the website, reported to the authorities and sued for damages. If you upload a virus that spreads to other users and causes damage and you are a student of the University, you will be banned from the website, reported to the authorities, sued for damages and expelled from the University. If you upload a virus that spreads to other users and causes damage and you are a student of the University and you are a foreigner, you will be banned from the website, reported to the authorities, sued for damages, expelled from the University and deported.</b>
    </p>
    Updates:
    <ul class="mb-6">
        <li>14. 7. 2023: Because of repeated questions, lets us point out again that the input file is fd 3 and desired output is fd 4.</li>
        <li>13. 7. 2023: We added new input files for the first two assignments. Due by tommorow.</li>
        <li>12. 7. 2023: We added a new motivation image for you. Please check it out.</li>
        <li>11. 7. 2023: We added a new motivation image for you. Please check it out.</li>
        <li>10. 7. 2023: We added a new motivation image for you. Please check it out.</li>
    </ul>
    </div>
    `
    let m = document.createElement('img');
    m.src = "/api/motivation?"+Date.now();
    m.style = "max-height: 70vh; width: auto; margin: auto;"
    document.getElementById('img').appendChild(m)
});

router.on('/login', function () {
    document.getElementById('app').innerHTML = `
<h1 class="title">Login</h1>
<div class="field">
<label class="label">Username</label>
<div class="control">
    <input class="input" type="text" name="username" placeholder="username">
</div>
</div>
<div class="field">
<label class="label">Password</label>
<div class="control">
    <input class="input" type="password" name="password" placeholder="password">
</div>
</div>
<div class="field">
<div class="control">
    <button class="button is-link" onclick="handleLogin()">Login</button>
</div>
</div>
    `
});

async function handleLogin() {
    let username = document.getElementsByName('username')[0].value
    let password = document.getElementsByName('password')[0].value
    try {
        await progcodex.login(username,password)
        router.navigate("/")
        updateMenu()
    } catch (err) {
        alert(err)
    }
}


router.on('/signup', function () {
    document.getElementById('app').innerHTML = `
<h1 class="title">Signup</h1>
<div class="field">
<label class="label">Username</label>
<div class="control">
    <input class="input" type="text" name="username" placeholder="username">
</div>
</div>
<div class="field">
<label class="label">Password</label>
<div class="control">
    <input class="input" type="password" name="password" placeholder="passwd">
</div>
</div>
<div class="field">
<div class="control">
    <button class="button is-link" onclick="handleRegister()">Register</button>
</div>
</div>
`
});

async function handleRegister() {
    let username = document.getElementsByName('username')[0].value
    let password = document.getElementsByName('password')[0].value
    try {
        await progcodex.signup(username,password)
        alert("Registration successful, now login please")
        router.navigate("/login")
    } catch (err) {
        alert(err)
    }
}


router.on('/logout', function () {
    progcodex.logout().then(()=>updateMenu())
    router.navigate('/')
});

router.on('/submissions', function () {
    document.getElementById('app').innerHTML = `
<h1 class="title">My Submissions</h1>
<table class="table">
<thead>
    <tr>
    <th>Name</th>
    </tr>
</thead>
<tbody id="mine">
</tbody>
</table>
<h1 class="title">Shared with me</h1>
<table class="table">
<thead>
    <tr>
    <th>Name</th>
    <th>Author</th>
    </tr>
</thead>
<tbody id="sharedwithme">
</tbody>
</table>
`
    progcodex.submissions().then(s => {
        document.querySelector("#mine").replaceChildren(...s['mine'].map(e=>{
            let tr = document.createElement('tr');
            let nametd = document.createElement('td');
            let a = document.createElement('a');
            a.innerText = e['name']
            a.setAttribute("onclick","router.navigate('/submissions/"+e['_id']+"')")
            nametd.appendChild(a)
            tr.appendChild(nametd)
            return tr
        }))

        document.querySelector("#sharedwithme").replaceChildren(...s['sharedwithme'].map(e=>{
            let tr = document.createElement('tr');
            let nametd = document.createElement('td');
            let a = document.createElement('a');
            a.innerText = e['name']
            a.setAttribute("onclick","router.navigate('/submissions/"+e['_id']+"')")
            nametd.appendChild(a)
            let authortd = document.createElement('td');
            authortd.innerText = e['author']
            tr.appendChild(nametd)
            tr.appendChild(authortd)
            return tr
        }))
    })
});

router.on('/stats', function () {
    document.getElementById('app').innerHTML = `
<h1 class="title">Stats</h1>
<input class="input" type="text" id="author" placeholder="search by author">
<button class="button is-link" onclick="handleStats()">Find</button>
<table class="table">
<thead>
    <tr>
    <th>Author</th>
    <th>Submissions</th>
    </tr>
</thead>
<tbody id="stats">
</tbody>
</table>
`
    progcodex.stats().then(s => {
        document.querySelector("#stats").replaceChildren(...s['statistics'].map(e=>{
            let tr = document.createElement('tr');
            let authortd = document.createElement('td');
            authortd.innerText = e['author']
            let counttd = document.createElement('td');
            counttd.innerText = e['count']
            tr.appendChild(authortd)
            tr.appendChild(counttd)
            return tr
        }))
    })
});

function handleStats() {
    let author = document.getElementById('author').value
    let filter = {}
    if (author) {
        filter['author'] = author
    }
    progcodex.stats(filter).then(s => {
        document.querySelector("#stats").replaceChildren(...s['statistics'].map(e=>{
            let tr = document.createElement('tr');
            let authortd = document.createElement('td');
            authortd.innerText = e['author']
            let counttd = document.createElement('td');
            counttd.innerText = e['count']
            tr.appendChild(authortd)
            tr.appendChild(counttd)
            return tr
        }))
    })
}

router.on('/new', function () {
    document.getElementById('app').innerHTML = `
<h1 class="title">Add submission</h1>
<div class="field">
<label class="label">Name</label>
<div class="control">
    <input class="input" type="text" id="name" placeholder="Number of inversions">
</div>
</div>
<div class="field">
<label class="label">File</label>
<div class="file">
  <label class="file-label">
    <input class="file-input" type="file" id="submission">
    <span class="file-cta">
      <span class="file-label">
        Upload submission
      </span>
    </span>
  </label>
</div>
</div>
`
    document.getElementById("submission").addEventListener('change', e => {
        if (e.target.files.length > 0) {
            getBase64(e.target.files[0]).then(d => {
                let file = d.toString().replace(/^data:(.*,)?/, '');
                let name = document.getElementById("name").value;

                progcodex.addSubmission(name, file).then(n => {
                    router.navigate('/submissions/'+n.id);
                }).catch(e=>alert(e))
            }).catch(e=>alert(e))
        }
    })
});

router.on('/submissions/:id', function ({data}) {
    document.getElementById('app').innerHTML = `
<h1 class="title" id="title"></h1>
<p class="mt-3" id="author"></p>
<p class="mt-3">
<pre><code id="dis"></code></pre>
</p>
<div class="buttons mt-6">
<button class="button is-danger" id="execute">Run</button>
<button class="button is-light" id="sharetoken">Get share token</button>
</div>
<p class="mt-3">
<pre><code id="out"></code></pre>
</p>
<div class="field">
<label class="label">Shared with</label>
<div class="control">
    <input class="input" type="text" id="sharedwith" placeholder="fzavoral,lvagner">
</div>
</div>
<div class="control">
  <button class="button is-primary" id="sharedwithupdate">Update shared with</button>
</div>
<h1 class="subtitle mt-6">Comments</h1>
<div id="comments">

</div>
<textarea class="textarea mt-6" id="newcomment" placeholder="Not enough encapsulation!!"></textarea>
<div class="control">
  <button class="button is-primary" id="newcommentpost">Post</button>
</div>
`
    progcodex.getSubmission(data.id).then(n => {
        document.getElementById('title').innerText = n.submission.name;
        document.getElementById('author').innerText = "By: "+n.submission.author;

        var binary_string = window.atob(n.payload);
        var len = binary_string.length;
        var bytes = new Uint8Array(len);
        for (var i = 0; i < len; i++) {
            bytes[i] = binary_string.charCodeAt(i);
        }
    

        let d = new cs.Capstone(cs.ARCH_X86, cs.MODE_32);
        let instructions = d.disasm(bytes, 0);

        let dis = "";

        instructions.forEach(function (instr) {
            dis += "0x"+instr.address.toString(16)+":\t"+instr.mnemonic+"\t"+instr.op_str+"\n"
        });
        
        document.getElementById('dis').innerText = dis;
        document.getElementById('sharedwith').value = n.submission.sharedwith.map(i => i["username"]).join(',');
        document.getElementById('sharedwithupdate').addEventListener('click', e => {
            let val = document.getElementById('sharedwith').value;
            progcodex.shareSubmission(data.id, val.split(',')).catch(e=>alert(e))
        })
        document.getElementById('sharetoken').addEventListener('click', e => {
            alert("Sharetoken: "+n.submission.sharetoken)
        })
        document.getElementById('execute').addEventListener('click', e => {
            inputid = prompt("Enter input id that you wish to run with:", "0");
            progcodex.executeSubmission(data.id, inputid).then(r => {
                document.getElementById('out').innerText = r.output;
            })
        })
        n.submission.comments.forEach((e) => {
            let art = document.createElement('article');
            art.classList = 'message'
            let bod = document.createElement('div')
            bod.classList = 'message-body'
            bod.innerText = e.author+" says: "+e.comment
            art.appendChild(bod)
            document.getElementById('comments').appendChild(art)
        })
        document.getElementById('newcommentpost').addEventListener('click', e => {
            let val = document.getElementById('newcomment').value;
            progcodex.addComment(data.id, val).catch(e=>alert(e))
        })
    }).catch(e=>alert(e))
});


window.addEventListener('DOMContentLoaded', (event) => {
    updateMenu()
});

async function updateMenu() {
    let menu = []
    try {
        user = await progcodex.me()
        menu = [
            [
                ["My submissions","/submissions"],
                ["New submission","/new"],
                ["Stats","/stats"],
            ],
            [
                ["User: "+user.username,"#"],
                ["Logout","/logout"],
            ]
        ]
    } catch (err) {
        menu = [
            [],
            [
                ["Login","/login"],
                ["Signup","/signup"],
            ]
        ]
    }
    document.querySelector(".navbar-start").replaceChildren(...menu[0].map(e=>{let a = document.createElement('a');a.classList = "navbar-item";a.setAttribute("onclick","router.navigate('"+e[1]+"')");a.innerText = e[0];return a}))
    document.querySelector(".navbar-end").replaceChildren(...menu[1].map(e=>{let a = document.createElement('a');a.classList = "navbar-item";a.setAttribute("onclick","router.navigate('"+e[1]+"')");a.innerText = e[0];return a}))
}

// ref https://stackoverflow.com/a/46639837
function getBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
    });
  }
  


router.resolve();
