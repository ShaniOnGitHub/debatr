import { OpenRouter } from "@openrouter/sdk";

import fs from "fs";

let apiKey = process.env.OPENROUTER_API_KEY;
if (!apiKey && fs.existsSync(".env")) {
  const envContent = fs.readFileSync(".env", "utf-8");
  const match = envContent.match(/OPENROUTER_API_KEY\s*=\s*(.+)/);
  if (match) apiKey = match[1].trim().replace(/^["']|["']$/g, '');
}

const openrouter = new OpenRouter({
  apiKey: apiKey || "YOUR_OPENROUTER_API_KEY"
});

const response = await openrouter.chat.send({
  chatRequest: {
    model: "stealth/union-alpha",
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text: "What is in this image?"
          },
          {
            type: "image_url",
            imageUrl: {
              url: "https://live.staticflickr.com/3851/14825276609_098cac593d_b.jpg"
            }
          }
        ]
      }
    ]
  }
});

console.log(response.choices[0].message.content);
