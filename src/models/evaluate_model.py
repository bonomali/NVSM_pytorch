from tqdm import tqdm
from sklearn.neighbors import NearestNeighbors
import numpy as np

def _extract_numpy_doc_embs(nvsm):
    '''
    Extract the document embedding from the PyTorch module in order
    to feed them to sklearn.neighbors.NearestNeighbors.
    '''
    return nvsm.doc_emb.weight.detach().cpu().numpy()

def generate_eval(k_values, recall_at_ks):
    '''
    Generates a string summarizing the various recall@k metrics. It is
    used as a logging function during the training of the model.
    '''
    s = [f'@{k}: {recall_at_k * 100:5.2f}%' for k, recall_at_k in zip(k_values, recall_at_ks)]
    recall_values = ' '.join(s)

    return f'R {recall_values}'

def evaluate(nvsm, device, eval_loader, recalls, loss_function):
    '''
    Evaluates the model by computing various recall@k on the validation set.
    The nearest neighbor search is done by a sklearn model and is computed
    using cosine distance.
    '''
    doc_embs = _extract_numpy_doc_embs(nvsm)
    nn_docs  = NearestNeighbors(n_neighbors = max(recalls), metric = 'cosine')
    nn_docs.fit(doc_embs)
    total_query  = 0
    doc_hit_at_k = [0] * len(recalls)
    tqdm_eval_loader = tqdm(
        enumerate(eval_loader),
        desc  = 'Eval batch',
        total = len(eval_loader),
        ncols = 70,
        leave = False
    )
    for i, (n_grams, doc_ids) in tqdm_eval_loader:
        total_query += n_grams.shape[0]
        n_grams      = n_grams.to(device)
        n_gram_embs  = nvsm.query_embedding(n_grams)
        n_gram_embs  = n_gram_embs.detach().cpu().numpy()
        neighbors    = nn_docs.kneighbors(n_gram_embs, return_distance = False)
        doc_ids      = doc_ids.numpy().reshape(-1, 1)
        hits         = neighbors == doc_ids
        for i, k in enumerate(recalls):
            doc_found_in_k_neigh  = np.any(hits[:, :k], axis = 1)
            doc_hit_at_k[i]      += doc_found_in_k_neigh.sum()

    return [hit_number / total_query for hit_number in doc_hit_at_k]
