# SAMU 192 · App Android (Capacitor)

App Android que abre o SAMU 192 do **servidor da unidade** (PC rodando o executável ou `python main.py`) e, sem acesso a ele, mostra a **última cópia do Firebase** em modo consulta.

```
android-app/
├── capacitor.config.json   # appId br.gov.samu192.estoque, HTTP liberado p/ IP local
├── package.json            # Capacitor 6
├── assets/                 # ícone + splash oficiais (gerados por backend/gerar_icones.py)
└── www/
    ├── index.html          # tela "Servidor da unidade" (IP + porta, salvo no aparelho)
    ├── offline.html        # consulta offline via Firebase Auth + Firestore
    └── estilo.css
```

## Como funciona
1. **Primeira abertura**: digite o IP mostrado em *Perfil → Modo rede local* no PC (ex.: `192.168.0.10`, porta `8765`) → **Testar e conectar**. O app testa `/healthz/`, salva o endereço e abre o login.
2. **Próximas aberturas**: reconecta sozinho em 3 s (botão *Trocar servidor* para mudar).
3. **Login** = mesmo usuário/senha do sistema. Com *Sincronizar ao fazer login* ativado no painel, o servidor envia o backup ao Firebase nesse momento.
4. **Consulta offline (Firebase)**: cole o `firebaseConfig` do app Web do seu projeto, entre com e-mail/senha do Firebase Auth e veja medicamentos, lotes, validades e frota (somente leitura). A cópia fica salva no aparelho para abrir até sem internet.

## Gerar o APK

### A) GitHub Actions (recomendado — nada para instalar)
`Save to GitHub` → GitHub → **Actions → Build APK Android** (roda em todo push em `android-app/**` ou em **Run workflow**) → baixe **SAMU192-android-apk** → instale no celular (permita *instalar apps desconhecidos*).

### B) Na sua máquina
Requisitos: Node 20+, JDK 17, Android Studio (SDK 34).
```bash
cd android-app
npm install
npx cap add android
npx capacitor-assets generate --android
npx cap sync android
npx cap open android        # Build → Build Bundle(s)/APK(s) → Build APK(s)
```
Garanta `android:usesCleartextTraffic="true"` na tag `<application>` do `android/app/src/main/AndroidManifest.xml` (o servidor local usa HTTP).

## Dicas
- Celular e PC **na mesma Wi-Fi**; libere a porta 8765 no Firewall do Windows (redes privadas).
- Exportar PDF/XLSX: faça pelo computador (WebView do Android não baixa arquivos).
- Trocou o logo? Rode `python backend/gerar_icones.py` e faça push — o APK sai com o ícone novo.
- APK assinado para Play Store: Android Studio → *Build → Generate Signed Bundle/APK*.
