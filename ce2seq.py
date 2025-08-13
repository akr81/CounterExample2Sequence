# %%
# SPINの反例からシーケンス図を生成する
import zlib
import re
import requests
import sys

# %%
COUNTEREXAMPLE = """
spin: main_original.pml:0, warning, proctype Agent, 'int   acked' variable is never used (other than in print stmnts)
spin: main_original.pml:0, warning, proctype DB, 'int   count' variable is never used (other than in print stmnts)
starting claim 3
MSC: ~G line 4
  1:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
Never claim moves to line 4	[(1)]
Starting Agent with pid 2
  2:	proc  0 (:init::1) main_original.pml:88 (state 1)	[(run Agent())]
Starting DB with pid 3
  3:	proc  0 (:init::1) main_original.pml:89 (state 2)	[(run DB())]
  4:	proc  0 (:init::1) main_original.pml:90 (state 3)	[Agent_ch!request_send]
  5:	proc  1 (Agent:1) main_original.pml:20 (state 1)	[Agent_ch?event]
  6:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
  7:	proc  2 (DB:1) main_original.pml:80 (state 33)	[(1)]
  8:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
  9:	proc  2 (DB:1) main_original.pml:81 (state 34)	[DB_state = stop]
 10:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 11:	proc  2 (DB:1) main_original.pml:77 (state 31)	[((DB_state==stop))]
 12:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 13:	proc  1 (Agent:1) main_original.pml:22 (state 2)	[(((Agent_state==ready)&&(event==request_send)))]
 14:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 15:	proc  2 (DB:1) main_original.pml:78 (state 32)	[DB_state = ready]
 16:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 17:	proc  1 (Agent:1) main_original.pml:23 (state 3)	[DB_ch!send_data]
 18:	proc  2 (DB:1) main_original.pml:44 (state 1)	[DB_ch?event]
 19:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 20:	proc  1 (Agent:1) main_original.pml:24 (state 4)	[Agent_state = sending]
MSC: ~G line 3
 21:	proc  - (spec1:1) _spin_nvr.tmp:3 (state 1)	[(!((!((Agent_state==sending))||(78==ready))))]
Never claim moves to line 3	[(!((!((Agent_state==sending))||(78==ready))))]
spin: _spin_nvr.tmp:3, Error: assertion violated
spin: text of failed assertion: assert(!(!((!((Agent_state==sending))||(78==ready)))))
#processes: 3
 22:	proc  2 (DB:1) main_original.pml:45 (state 20)
 22:	proc  1 (Agent:1) main_original.pml:19 (state 14)
 22:	proc  0 (:init::1) main_original.pml:92 (state 5)
 22:	proc  - (spec1:1) _spin_nvr.tmp:3 (state 2)
3 processes created
Exit-Status 0

"""

# PlantUMLサーバのURLを設定
SERVER = "https://www.plantuml.com/plantuml/png/"

# %%
pattern = r"""
    ^\s*           # 行頭の空白
    (\d+)          # step番号
    :\s*proc\s*    # プロセス
    \d+\s*         # プロセス番号を読み飛ばす
    \(
        ([^)]+)    # プロセス名
    \)\s+
    ([^\s]+:\d+)   # ファイル名と行番号
    \s*\(state\s*\d+\)\s*  # SPINの内部状態を読み飛ばす
    \[
        (.+?)      # 処理
    \]
    \s*$           # 行末の空白
"""


# %%
## PlantUMLサーバ向けのエンコード関数
def encode_plantuml(text: str) -> str:
    """Encode text to PlantUML server format.

    Args:
        text (str): Text to encode

    Returns:
        str: Encoded text
    """
    # UTF-8にエンコードし、zlibでdeflate圧縮
    data = text.encode("utf-8")
    compressed = zlib.compress(data)
    # zlibヘッダー(最初の2バイト)とチェックサム(最後の4バイト)を除去
    compressed = compressed[2:-4]
    return encode64(compressed)


def encode64(data: bytes) -> str:
    """Encode bytes to PlantUML server format.

    Args:
        data (bytes): Data to encode

    Returns:
        str: Encoded text
    """
    # PlantUML用のカスタム64エンコードテーブル
    char_map = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    res = []
    # 3バイトずつ処理し、24ビット整数にまとめる
    for i in range(0, len(data), 3):
        b = data[i : i + 3]
        # 3バイトに満たない場合は0でパディング
        if len(b) < 3:
            b = b + bytes(3 - len(b))
        n = (b[0] << 16) + (b[1] << 8) + b[2]
        # 6ビットごとに分割して、char_mapの文字に変換
        res.append(char_map[(n >> 18) & 0x3F])
        res.append(char_map[(n >> 12) & 0x3F])
        res.append(char_map[(n >> 6) & 0x3F])
        res.append(char_map[n & 0x3F])
    return "".join(res)


def get_participants(counter_example: str) -> str:
    """Extract unique participants from the counter example.

    Args:
        counter_example (str): Counter example output from SPIN

    Returns:
        str: PlantUML participants code
    """
    participants = set()
    for line in counter_example.splitlines():
        line = line.strip()
        m = re.match(pattern, line, re.VERBOSE)
        if m:
            _, process_name, _, _ = m.groups()
            participants.add(process_name)
    # プロセス名をアルファベット順にソート
    participants = sorted(participants)

    # PlantUMLのparticipantsとして出力
    ret = ""
    for participant in participants:
        ret += f'participant "{participant}"\n'

    return ret


def convert_to_plantuml_code(counter_example: str) -> str:
    """Convert a single step to PlantUML code.

    Args:
        counter_example (str): Counter example output from SPIN

    Returns:
        str: PlantUML code
    """
    ret = ""

    # 反例の出現順に列が並ぶと毎回変わってしまうので、一度読み込んで辞書順に並べる
    ret += get_participants(counter_example)

    loop = False
    for line in counter_example.splitlines():
        line = line.strip()
        m = re.match(pattern, line, re.VERBOSE)
        if m:
            step_num, process_name, file_line, action = m.groups()
        elif "<<<<<START OF CYCLE>>>>>" in line:
            # ループの開始を検出
            ret += "loop CYCLE\n"
            loop = True
            continue
        else:
            continue

        # Promelaの行番号を取得
        line_num = "l." + file_line.split(":")[-1]

        # 通常はsource, destinationは自プロセス
        source = process_name
        destination = process_name
        arrow = "->"

        # actionがchへの書き込み・読み込み場合はsourceとdestinationを分ける
        if "!" in action:
            # 書き込みの場合
            destination, action = action.split("!")
        elif "?" in action:
            # 読み込みの場合
            source, action = action.split("?")
            arrow = "-->"

        ret += (
            f'"{source}" {arrow} "{destination}" : s.{step_num}: {line_num}: {action}\n'
        )

    if loop:
        ret += "end\n"

    return ret


# %%
def main():
    plantuml_code = f"""
@startuml
scale 2.0
"""
    # 引数がなければサンプルとしてCOUNTEREXAMPLEを使用
    print(sys.argv)
    if len(sys.argv) < 2:
        print("反例のファイルパスを引数として指定してください。")
        print("サンプルデータを使用します。")
        counter_example = COUNTEREXAMPLE
    else:
        with open(sys.argv[1], "r") as f:
            counter_example = f.read()

    plantuml_code += convert_to_plantuml_code(counter_example)
    plantuml_code += "@enduml\n"
    print(plantuml_code)

    # PlantUMLサーバ用にエンコード
    encoded = encode_plantuml(plantuml_code)
    url = "".join([SERVER, encoded])
    response = requests.get(url)
    if response.status_code == 200:
        pass
    else:
        print("サーバから画像を取得できませんでした")
    with open("sequence_diagram.png", "wb") as out:
        out.write(response.content)


# %%
if __name__ == "__main__":
    main()

# %%
