from tqdm import tqdm

if __name__ == '__main__':
    for i in tqdm(range(0, 21), desc='computing a set of lemada tables:'):
        NOD_TTT = pd.read_csv(f'{TABLE_PATH}mean-table.csv', index_col=0)
        print(NOD_TTT.head(2))
