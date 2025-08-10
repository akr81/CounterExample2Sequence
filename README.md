# CounterExample2Sequence

SPINの実行結果(反例)をシーケンス図、または変数テーブルに変換します。

## 環境

変数テーブルへの変換には`pandas`を使用しているため、必要に応じてインストールしてください。

```shell
# 例
pip install pandas
```

## 使用方法

### シーケンス図に変換

コマンドラインから、SPINの実行結果ファイルを引数として実行します。

```shell
python ce2seq.py FILE
```

成功すると、`sequence_diagram.png`が作成されます。  
また、PlantUMLのコード文字列が表示されます。

#### 制限事項

PlantUMLは出力画像の最大ピクセル数に制限があります。  
反例が長い場合は途中で切れてしまうため、あらかじめ関心がある部分だけを取り出すなどしてください。

### 変数テーブルに変換

コマンドラインから、SPINの実行結果ファイルを引数として実行します。

```shell
python ce2table.py FILE
```

成功すると、`variable_table.csv`が作成されます。  


## 注意事項

PlantUMLの公開サーバを利用しているため、機微な情報の送信にはご注意ください。  
ローカルで実行しているPlantUMLサーバを利用する場合には、以下の部分を書き換えるようにしてください。

```python
# PlantUMLサーバのURLを設定
SERVER = "https://www.plantuml.com/plantuml/png/"
```
