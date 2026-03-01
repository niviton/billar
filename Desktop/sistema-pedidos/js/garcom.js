import { db } from "./firebase-config.js";
import { collection, addDoc } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

async function enviarPedido() {
    const mesa = document.getElementById("mesa").value;
    const pedido = document.getElementById("pedido").value;
    const observacao = document.getElementById("observacao").value;

    if (mesa && pedido) {
        await addDoc(collection(db, "pedidos"), {
            mesa,
            pedido,
            observacao,
            status: "Em preparo"
        });
        alert("Pedido enviado!");
    } else {
        alert("Preencha todos os campos!");
    }
}
