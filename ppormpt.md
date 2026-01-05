你是資深 DevOps/Repo maintainer。目標：在「既有 Git 專案」中導入 Git LFS 並補齊 .gitignore，符合業界乾淨可維護標準，且不把模型/音檔/金鑰/本機依賴提交進 git history。

請在開始前先做現況盤點（輸出你看到的狀態）：
1) git status、git remote -v、目前是否已啟用 git lfs（git lfs env / git lfs track）
2) 專案根目錄是否已有：.gitignore、.gitattributes、.env 或 secrets、models/、audio_outputs/、logs/、piper/ 等資料夾
3) repo 是否已經 commit 過大型二進位（onnx/pt/bin/wav/pcm/mp3），若有請列出檔名與大小，並提醒「是否需要 lfs migrate」但不要直接改寫 history，除非我明確要求。

接著請按「既有專案加入 LFS」標準流程執行並產出可複製的指令：
- git lfs install
- 建立或更新 .gitattributes，追蹤至少：
  *.onnx, *.pt, *.bin
  （音檔 *.wav 先不要預設追蹤，除非我說要）
- git add .gitattributes
- git commit -m "chore: enable git lfs for large assets"

然後補齊/更新 .gitignore（若已存在則在不破壞原規則下合併），至少包含：
- Env / secrets：.env、.env.*，但保留 !.env.example
- Logs / outputs：logs/*.json、*.log
- Audio artifacts：*.wav、*.pcm、*.mp3、audio_outputs/**，但保留 audio_outputs/.gitignore
- Models：models/**，但保留 models/.gitignore
- Local vendor binaries：piper/
- IDE / OS 垃圾檔維持忽略（.vscode/.idea/Thumbs.db 等）

同時請幫我建立兩個空的佔位檔（確保資料夾會被 git 追蹤但內容被忽略）：
- models/.gitignore
- audio_outputs/.gitignore
內容請使用「只保留自身 .gitignore」的寫法。

最後輸出：
A) 你實際要我執行的命令清單（PowerShell 與 bash 各一份）
B) .gitattributes 完整內容
C) .gitignore 最終內容（合併後）
D) 風險提醒：如果已經有大檔進了 history，下一步建議怎麼做（僅建議，不要自動 migrate）

