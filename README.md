**🎉 Welcome to the Answer Rating System! 🎉**

Ever wondered how close your answer is to being spot-on? With our Answer Rating System, you'll get a rating between 0 and 100 to see just how well you did. We’ve got some AI magic happening here with SpaCy and Groq models working together to give you the most accurate score possible!

---

**✨ Features That’ll Amaze You:**

- **Backend Awesomeness:**
  - Built with Flask – lightweight, but oh so powerful!
  - SpaCy is our secret sauce for understanding text.
  - Groq steps in with advanced AI for rating answers like a pro.
  - Two cool endpoints:
    - `/api/spacy-rate`: SpaCy rates your answers.
    - `/api/groq-rate`: Groq takes a shot at rating too.

- **Frontend Simplicity:**
  - A clean, responsive design with HTML, CSS, and JavaScript.
  - Input your answer, hit submit, and boom – your ratings from both models appear!
  - Easy to use and visually pleasing, just the way you like it.

---

**🚀 Let’s Get You Started:**

**What You’ll Need:**
- Python 3.11+ (because we like the new stuff!)
- Node.js (if you fancy tinkering with the frontend)
- Flask, Flask-CORS, SpaCy, Gunicorn (backend superpowers)

**Backend Setup (Magic Happens Here):**

1. Clone this repo and dive in:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. Set up a virtual playground:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install all the goodies:
   ```bash
   pip install -r requirements.txt
   ```

4. Fire up the server:
   ```bash
   flask run
   ```

5. Going live? Use Gunicorn:
   ```bash
   gunicorn app:app
   ```

**Frontend Setup (Let’s Go Visual):**

1. Open `index.html` in your favorite browser.
2. Play around and see the magic happen!
3. Want to share? Deploy it on GitHub Pages, Netlify, or Vercel.

---

**🔮 Endpoints – Where the Magic Lives:**

- `POST /api/spacy-rate`: Let SpaCy rate your answers.
  - **Send this:**
    ```json
    {
      "userAnswer": "Your answer here",
      "correctAnswer": "Correct answer here"
    }
    ```

- `POST /api/groq-rate`: Groq will also give it a try.
  - **Send this:**
    ```json
    {
      "userAnswer": "Your answer here",
      "correctAnswer": "Correct answer here"
    }
    ```

---

**🌐 CORS Configuration – No Blockages Here!**

We’ve enabled CORS to keep things smooth between the frontend and backend. Only specific origins get through – tight security, no worries!

---

**📡 Deployment**

Check out the live version here: [Daedalus Server](https://daedalus-server.onrender.com/). Host your frontend on your favorite static hosting service.

---

**📜 License**

Feel free to fork and star – it’s all under the MIT License. See the `LICENSE` file for details.

---

**💡 Acknowledgments**

Big shoutout to Flask, SpaCy, and Groq for powering this project. Your tools make the magic happen!

---
