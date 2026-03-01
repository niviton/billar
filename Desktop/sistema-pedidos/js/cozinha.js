import { db } from "./firebase-config.js";
import { collection, query, onSnapshot, updateDoc, doc } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

const pedidosDiv = document.getElementById("pedidos");

// Monitorando novos pedidos em tempo real
const q = query(collection(db, "pedidos"));
onSnapshot(q, (snapshot) => {
    pedidosDiv.innerHTML = "";
    snapshot.forEach((docSnap) => {
        const pedido = docSnap.data();
        const pedidoId = docSnap.id;

        const pedidoElement = document.createElement("div");
        pedidoElement.innerHTML = `
            <p><strong>Mesa:</strong> ${pedido.mesa}</p>
            <p><strong>Pedido:</strong> ${pedido.pedido}</p>
            <p><strong>Observação:</strong> ${pedido.observacao}</p>
            <p><strong>Status:</strong> ${pedido.status}</p>
            <button onclick="marcarComoPronto('${pedidoId}')">Marcar como Pronto</button>
            <hr>
        `;
        pedidosDiv.appendChild(pedidoElement);
    });
});

window.marcarComoPronto = async (id) => {
    const pedidoRef = doc(db, "pedidos", id);
    await updateDoc(pedidoRef, { status: "Pronto" });
};
