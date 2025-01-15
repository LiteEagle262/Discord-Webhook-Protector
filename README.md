# Discord-Webhook-Protector

Discord-Webhook-Protector is a simple, FastAPI-powered app that safeguards your Discord webhooks. By acting as a relay, it protects your webhooks from spamming and unauthorized deletion, ensuring they remain secure.

---

## Installation

There is two ways of using this app, deploying it on your own (Im not going to make a guide for that but its simple)
or to use my free to use and fully deployed one: [https://dcrelay.liteeagle.me](https://dcrelay.liteeagle.me/).

It's pretty simple to use, you input a discord webhook onto the site, click create, and it will output you a relay URL, you just replace wherever your webhook was with that relay URL
and your good, no one can delete your webhook, and no one can spam it/rate limit it.

## Use Case

This simple app is usefull for anyone deploying code with a webhook in a front end enviroment (EX: Compiled App, or very uncommonly Front end JS on a website.)

---

## Features

### **Rate Limiting**
- Prevent spamming by implementing a robust rate-limiting system. 
- If the same content is sent twice, the sender will be rate-limited for **15+ seconds**, avoiding duplicate submissions and potential abuse.

### **Webhook Deletion Protection**
- **Did you know?** Anyone can delete your webhook with just one DELETE request. 
- With This Relay, such actions are impossible without the actual webhook URL. 
- This tool acts as a layer of defense, keeping your webhooks secure from tampering.

---

## How It Works
- All webhook requests are sent to this app instead of directly to the Discord webhook.
- The app forwards the requests while ensuring they comply with rate limits and access controls.
- Your actual Discord webhook URL remains hidden and safe.

---

## Donate

```
BTC: bc1qvycuvdsrx5zatr7qvzlsnkej0d65fpsmrqv3m7
LTC: LS9L28s8xbBNYzsWgBq3jxpVmprBH5Ep19
ETH: 0x4e37e749a61f22e5b64C625D41830416E043D829
SOL: 2HoCrwm9CAoZZNtzGDGVvMUy7NVxpc49zG2Am7YTZ8Gj
```
