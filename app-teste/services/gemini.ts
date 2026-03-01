
import { GoogleGenAI, Type } from "@google/genai";
import { LyricsResponse, Suggestion } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const generateProductionIdeas = async (mood: string): Promise<Suggestion[]> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Generate 3 music production ideas for a ${mood} mood. Provide a title, description, genre, and recommended BPM for each.`,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            title: { type: Type.STRING },
            description: { type: Type.STRING },
            genre: { type: Type.STRING },
            bpm: { type: Type.NUMBER }
          },
          required: ["title", "description", "genre", "bpm"]
        }
      }
    }
  });

  // Use .text property directly and provide a fallback to avoid JSON.parse errors
  const text = response.text || '[]';
  return JSON.parse(text);
};

export const generateLyrics = async (theme: string): Promise<LyricsResponse> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Write catchy, short lyrics (1 verse and 1 chorus) about ${theme}. Keep it musical and rhythmic.`,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          lyrics: { type: Type.STRING },
          mood: { type: Type.STRING }
        },
        required: ["lyrics", "mood"]
      }
    }
  });

  // Use .text property directly and provide a fallback to avoid JSON.parse errors
  const text = response.text || '{}';
  return JSON.parse(text);
};

export const generateCoverArt = async (prompt: string): Promise<string> => {
  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash-image',
    contents: {
      parts: [{ text: `High quality music album cover art for a track about: ${prompt}. Artistic, vibrant, professional graphic design.` }]
    },
    config: {
      imageConfig: {
        aspectRatio: "1:1"
      }
    }
  });

  // Find the image part by iterating through all parts in the response as per guidelines
  const parts = response.candidates?.[0]?.content?.parts || [];
  for (const part of parts) {
    if (part.inlineData) {
      const base64EncodeString: string = part.inlineData.data;
      return `data:image/png;base64,${base64EncodeString}`;
    }
  }
  return '';
};
