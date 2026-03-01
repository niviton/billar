import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// Configuração do Firebase
const firebaseConfig = {
  apiKey: "AIzaSyDVRDL0OBd1nAz_0jIaseNSRxtb0fyrZpQ",
  authDomain: "restaurante-d7c74.firebaseapp.com",
  projectId: "restaurante-d7c74",
  storageBucket: "restaurante-d7c74.appspot.com",  // Corrigido o domínio do storage
  messagingSenderId: "454769260834",
  appId: "1:454769260834:web:e732822d4b06ef0fda8d7b",
  measurementId: "G-NW1C8SDBZC"
};

// Inicializa o Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);  // Adicionando Firestore para armazenar pedidos

export { db };
