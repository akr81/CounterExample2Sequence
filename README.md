# CounterExample2Sequence

SPINの実行結果(反例)をシーケンス図に変換します。

## 使用方法

コマンドラインから、SPINの実行結果ファイルを引数として実行します。

```shell
python ce2seq.py FILE
```

成功すると、`sequence_diagram.png`が作成されます。  
また、PlantUMLのコード文字列が表示されます。

## 注意事項

PlantUMLの公開サーバを利用しているため、機微な情報の送信にはご注意ください。  
ローカルで実行しているPlantUMLサーバを利用する場合には、以下の部分を書き換えるようにしてください。

```python
# PlantUMLサーバのURLを設定
SERVER = "https://www.plantuml.com/plantuml/png/"
```
