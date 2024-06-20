import torch
import torch.nn as nn
from .architecture import (
    BartConfig,
    BartEncoder,
    BartDecoder,
    BartEmbeds,
    BartEncoderOut,
    BartDecoderOut,
    _init_weights,
)

class BartSeq2seqConfig(BartConfig):
    def __init__(
        self,
        share_tgt_emb_and_out: bool=False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.bart_config = BartConfig(**kwargs)
        self.share_tgt_emb_and_out = share_tgt_emb_and_out

class BartSeq2seq(nn.Module):
    def __init__(
        self,
        config: BartSeq2seqConfig,
    ):
        super().__init__()

        # config
        self.config = config
        # encoder_embeds
        self.inputs_embeds = BartEmbeds(
            num_embeddings=self.config.src_vocab_size,
            embedding_dim=config.d_model,
            padding_idx=config.pad_idx,
            max_position_embeddings=config.max_position_embeddings,
            init_std=config.init_std,
            type_attn=config.type_attn,
        )
        # decoder_embeds
        self.decoder_inputs_embeds = BartEmbeds(
            num_embeddings=self.config.tgt_vocab_size,
            embedding_dim=config.d_model,
            padding_idx=config.pad_idx,
            max_position_embeddings=config.max_position_embeddings,
            type_attn=config.type_attn,
        )
        # encoder, decoder
        self.encoder = BartEncoder(config.bart_config)
        self.decoder = BartDecoder(config.bart_config)
        # out
        self.out = nn.Linear(config.d_model, config.tgt_vocab_size)
        # Initialize weights
        self.apply(lambda module: _init_weights(
            module=module,
            std=config.init_std,
        ))

    def forward(
        self,
        attention_mask: torch.Tensor,
        decoder_input_ids: torch.Tensor,
        decoder_attention_mask: torch.Tensor,
        label: torch.Tensor=None,
        input_ids: torch.Tensor=None,
        inputs_embeds: torch.Tensor=None,
    ):
        # encoder
        if inputs_embeds is not None:
            encoder_hidden_states = self.encoder(
                inputs_embeds=self.inputs_embeds(
                    inputs_embeds=inputs_embeds,
                ),
                attention_mask=attention_mask,
            )
        else:
            encoder_hidden_states = self.encoder(
                inputs_embeds=self.inputs_embeds(
                    input_ids=input_ids,
                ),
                attention_mask=attention_mask,
            )
        # decoder
        decoder_hidden_states = self.decoder(
            inputs_embeds=self.decoder_inputs_embeds(decoder_input_ids),
            attention_mask=decoder_attention_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=attention_mask,
        )
        # out
        logits = self.out(decoder_hidden_states)

        if label is not None:
            if self.config.pad_idx is not None:
                loss_fn = nn.CrossEntropyLoss(
                    ignore_index=self.config.pad_idx,
                    label_smoothing=self.config.label_smoothing,
                )
            else:
                loss_fn = nn.CrossEntropyLoss(label_smoothing=self.config.label_smoothing)
            loss = loss_fn(logits.view(-1, self.config.tgt_vocab_size), label.view(-1))
            return logits, loss
        else:
            return logits
    
    def get_encoder_out(
        self,
        attention_mask: torch.Tensor,
        input_ids: torch.Tensor=None,
        inputs_embeds: torch.Tensor=None,
    ):
        if inputs_embeds is not None:
            encoder_out = self.encoder(
                inputs_embeds=self.inputs_embeds(
                    inputs_embeds=inputs_embeds,
                ),
                attention_mask=attention_mask,
            )
        else:
            encoder_out = self.encoder(
                inputs_embeds=self.inputs_embeds(
                    input_ids=input_ids,
                ),
                attention_mask=attention_mask,
            )

        return BartEncoderOut(
            logits=encoder_out,
        )
    
    def get_decoder_out(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        encoder_hidden_states: torch.Tensor,
        encoder_attention_mask: torch.Tensor,
    ):
        decoder_out = self.decoder(
            inputs_embeds=self.decoder_inputs_embeds(input_ids),
            attention_mask=attention_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
        )

        return BartDecoderOut(
            logits=decoder_out,
        )
    
def get_model(
    **kwargs,
):
    config = BartSeq2seqConfig(**kwargs)
    model = BartSeq2seq(
        config=config,
    )
    return model
    
__all__ = ["BartSeq2seq", "get_model"]