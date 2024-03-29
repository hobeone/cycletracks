/**
 * Software License Agreement (BSD License)
 * 
 * Copyright (c) 2008, Dave Hauenstein
 * All rights reserved.
 * 
 * Redistribution and use of this software in source and binary forms, with or
 * without modification, are permitted provided that the following conditions
 * are met:
 * 
 * - Redistributions of source code must retain the above copyright notice,
 *   this list of conditions and the following disclaimer.
 * 
 * - Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimer in the documentation
 *   and/or other materials provided with the distribution.
 * 
 * - Neither the name of Dave Hauenstein nor the names of its contributors may be
 *   used to endorse or promote products derived from this software without
 *   specific prior written permission of Dave Hauenstein
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

jQuery.fn.editInPlace=function(options){var settings={url:"",params:"",field_type:"text",select_options:"",textarea_cols:"25",textarea_rows:"10",bg_over:"#ffc",bg_out:"transparent",saving_text:"Saving...",saving_image:"",default_text:"(Click here to add text)",select_text:"Choose new value",value_required:null,element_id:"element_id",update_value:"update_value",original_html:"original_html",save_button:'<input type="submit" class="inplace_save" value="Save"/>',cancel_button:'<input type="submit" class="inplace_cancel" value="Cancel"/>',show_buttons:false,on_blur:"save",callback:null,success:null,error:function(request){alert("Failed to save value: "+request.responseText||'Unspecified Error')}};if(options){jQuery.extend(settings,options)}if(settings.saving_image!=""){var loading_image=new Image();loading_image.src=settings.saving_image}String.prototype.trim=function(){return this.replace(/^\s+/,'').replace(/\s+$/,'')};String.prototype.escape_html=function(){return this.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")};return this.each(function(){if(jQuery(this).html()=="")jQuery(this).html(settings.default_text);var editing=false;var original_element=jQuery(this);var click_count=0;jQuery(this).mouseover(function(){jQuery(this).css("background",settings.bg_over)}).mouseout(function(){jQuery(this).css("background",settings.bg_out)}).click(function(){click_count++;if(!editing){editing=true;var original_html=jQuery(this).html();var buttons_code=(settings.show_buttons)?settings.save_button+' '+settings.cancel_button:'';if(original_html==settings.default_text)jQuery(this).html('');if(settings.field_type=="textarea"){var use_field_type='<textarea name="inplace_value" class="inplace_field" rows="'+settings.textarea_rows+'" cols="'+settings.textarea_cols+'">'+jQuery(this).text().trim().escape_html()+'</textarea>'}else if(settings.field_type=="text"){var use_field_type='<input type="text" name="inplace_value" class="inplace_field" value="'+jQuery(this).text().trim().escape_html()+'" />'}else if(settings.field_type=="select"){var optionsArray=settings.select_options.split(',');var use_field_type='<select name="inplace_value" class="inplace_field"><option value="">'+settings.select_text+'</option>';for(var i=0;i<optionsArray.length;i++){var optionsValuesArray=optionsArray[i].split(':');var use_value=optionsValuesArray[1]||optionsValuesArray[0];var selected=use_value==original_html?'selected="selected" ':'';use_field_type+='<option '+selected+'value="'+use_value.trim().escape_html()+'">'+optionsValuesArray[0].trim().escape_html()+'</option>'}use_field_type+='</select>'}jQuery(this).html('<form class="inplace_form" style="display: inline; margin: 0; padding: 0;">'+use_field_type+' '+buttons_code+'</form>')}if(click_count==1){function cancelAction(){editing=false;click_count=0;original_element.css("background",settings.bg_out);original_element.html(original_html);return false}function saveAction(){original_element.css("background",settings.bg_out);var this_elem=jQuery(this);var new_html=(this_elem.is('form'))?this_elem.children(0).val():this_elem.parent().children(0).val();if(settings.saving_image!=""){var saving_message='<img src="'+settings.saving_image+'" alt="Saving..." />'}else{var saving_message=settings.saving_text}original_element.html(saving_message);if(settings.params!=""){settings.params="&"+settings.params}if(settings.callback){html=settings.callback(original_element.attr("id"),new_html,original_html,settings.params);editing=false;click_count=0;if(html){original_element.html(html||new_html)}else{alert("Failed to save value: "+new_html);original_element.html(original_html)}}else if(settings.value_required&&(new_html==""||new_html==undefined)){editing=false;click_count=0;original_element.html(original_html);alert("Error: You must enter a value to save this field")}else{jQuery.ajax({url:settings.url,type:"POST",data:settings.update_value+'='+new_html+'&'+settings.element_id+'='+original_element.attr("id")+settings.params+'&'+settings.original_html+'='+original_html,dataType:"html",complete:function(request){editing=false;click_count=0},success:function(html){var new_text=html||settings.default_text;original_element.html(new_text);if(settings.success)settings.success(html,original_element)},error:function(request){original_element.html(original_html);if(settings.error)settings.error(request,original_element)}})}return false}original_element.children("form").children(".inplace_field").focus().select();original_element.children("form").children(".inplace_cancel").click(cancelAction);original_element.children("form").children(".inplace_save").click(saveAction);if(!settings.show_buttons){if(settings.on_blur=="save")original_element.children("form").children(".inplace_field").blur(saveAction);else original_element.children("form").children(".inplace_field").blur(cancelAction)}$(document).keyup(function(event){if(event.keyCode==27){cancelAction()}});original_element.children("form").submit(saveAction)}})})};
